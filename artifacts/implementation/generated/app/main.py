"""
Main application entry point for the POS System Backend.

This module initializes the FastAPI application, configures middleware,
includes API routers, and manages application lifecycle events such as
database, Redis, and RabbitMQ connections.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
import redis.asyncio as aioredis
import aio_pika

from app.config.settings import settings
from app.config.database import engine, Base
from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as product_router
from app.api.v1.sales import router as sales_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.transfers import router as transfer_router
from app.api.v1.reports import router as report_router
from app.api.v1.users import router as user_router
from app.api.middleware.logging_middleware import LoggingMiddleware
from app.api.middleware.auth_middleware import AuthMiddleware
from app.api.middleware.rbac_middleware import RBACMiddleware
from app.api.middleware.error_middleware import ErrorHandlingMiddleware

# Initialize logging for the application
logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
logger = logging.getLogger(settings.APP_NAME)

# Global clients for Redis and RabbitMQ, initialized during application startup
redis_client: aioredis.Redis | None = None
rabbitmq_connection: aio_pika.RobustConnection | None = None
rabbitmq_channel: aio_pika.Channel | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Context manager for managing the lifespan of the FastAPI application.

    This function handles startup and shutdown events for critical services
    like the PostgreSQL database, Redis cache, and RabbitMQ message broker.
    It ensures resources are properly initialized before the application starts
    serving requests and gracefully closed upon shutdown.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: The application runs within this context.
    """
    logger.info(f"Starting up {settings.APP_NAME} v{settings.APP_VERSION} in {settings.ENVIRONMENT} environment...")

    # 1. Database startup: Create tables if they don't exist (for dev/test)
    try:
        # In a production environment, database migrations (e.g., Alembic)
        # should be used instead of Base.metadata.create_all().
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables checked/created.")
    except OperationalError as e:
        logger.critical(f"Failed to connect to database on startup: {e}")
        raise RuntimeError("Database connection failed on startup. Exiting.") from e

    # 2. Redis startup: Initialize and connect to Redis
    try:
        global redis_client
        redis_client = aioredis.from_url(str(settings.REDIS_URL))
        await redis_client.ping()  # Test the connection
        logger.info("Redis client initialized and connected.")
    except Exception as e:
        logger.critical(f"Failed to connect to Redis on startup: {e}")
        raise RuntimeError("Redis connection failed on startup. Exiting.") from e

    # 3. RabbitMQ startup: Initialize and connect to RabbitMQ
    try:
        global rabbitmq_connection, rabbitmq_channel
        rabbitmq_connection = await aio_pika.connect_robust(str(settings.RABBITMQ_URL))
        rabbitmq_channel = await rabbitmq_connection.channel()
        logger.info("RabbitMQ client initialized and connected.")

        # Declare necessary queues, ensuring they are durable
        await rabbitmq_channel.declare_queue(settings.RABBITMQ_QUEUE_SALES_EVENTS, durable=True)
        await rabbitmq_channel.declare_queue(settings.RABBITMQ_QUEUE_INVENTORY_EVENTS, durable=True)
        await rabbitmq_channel.declare_queue(settings.RABBITMQ_QUEUE_TRANSFER_EVENTS, durable=True)
        await rabbitmq_channel.declare_queue(settings.RABBITMQ_QUEUE_SYNC_OFFLINE, durable=True)
        logger.info("RabbitMQ queues declared.")
    except Exception as e:
        logger.critical(f"Failed to connect to RabbitMQ on startup: {e}")
        raise RuntimeError("RabbitMQ connection failed on startup. Exiting.") from e

    yield  # The application will now start serving requests

    # 4. Shutdown events: Gracefully close connections
    logger.info("Shutting down application...")

    if rabbitmq_channel:
        await rabbitmq_channel.close()
        logger.info("RabbitMQ channel closed.")
    if rabbitmq_connection:
        await rabbitmq_connection.close()
        logger.info("RabbitMQ connection closed.")

    if redis_client:
        await redis_client.close()
        logger.info("Redis client closed.")

    logger.info("Application shutdown complete.")


# Initialize the FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="Cloud-based Point of Sale (POS) system API.",
    lifespan=lifespan  # Assign the lifespan context manager
)

# Configure and add middleware to the application
# Middleware order is crucial:
# 1. Logging: Captures all requests/responses.
# 2. CORS: Handles cross-origin requests.
# 3. Auth: Authenticates users via JWT.
# 4. RBAC: Authorizes users based on roles.
# 5. Error Handling: Catches and formats exceptions.
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)
app.add_middleware(AuthMiddleware)
app.add_middleware(RBACMiddleware)
app.add_middleware(ErrorHandlingMiddleware)


# Include API routers for different functional modules
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(user_router, prefix="/api/v1", tags=["User Management"])
app.include_router(product_router, prefix="/api/v1", tags=["Product Management"])
app.include_router(sales_router, prefix="/api/v1", tags=["Sales Transactions"])
app.include_router(inventory_router, prefix="/api/v1", tags=["Inventory Management"])
app.include_router(transfer_router, prefix="/api/v1", tags=["Inventory Transfers"])
app.include_router(report_router, prefix="/api/v1", tags=["Reporting"])


@app.get("/", summary="Root endpoint for API health check", response_model=dict[str, Any])
async def root() -> dict[str, Any]:
    """
    Root endpoint providing basic information about the API.

    This endpoint can be used as a simple health check to verify that the
    application is running and responsive.

    Returns:
        dict[str, Any]: A dictionary containing the application name and version.
    """
    return {"app_name": settings.APP_NAME, "version": settings.APP_VERSION}