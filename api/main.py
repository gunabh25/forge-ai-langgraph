"""Main entry point for ForgeAI FastAPI Server."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config.logging import get_logger

from api.routers import generate, update, feedback, execution, health, monitoring

logger = get_logger("api.main")

tags_metadata = [
    {"name": "Generation", "description": "Endpoints for generating new architectures from scratch."},
    {"name": "Updates", "description": "Endpoints for incremental updates and change analysis."},
    {"name": "Feedback", "description": "Endpoints for submitting feedback for the ART component."},
    {"name": "Execution", "description": "Endpoints for managing and querying workflow executions and artifacts."},
    {"name": "Monitoring", "description": "Endpoints for system-wide performance metrics and observability."},
    {"name": "Health", "description": "API health checks."},
]

app = FastAPI(
    title="ForgeAI API",
    description="Production REST API for the ForgeAI Engineering Platform",
    version="1.0.0",
    openapi_tags=tags_metadata
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(generate.router, prefix="/api/v1", tags=["Generation"])
app.include_router(update.router, prefix="/api/v1", tags=["Updates"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
app.include_router(execution.router, prefix="/api/v1", tags=["Execution"])
app.include_router(monitoring.router, prefix="/api/v1", tags=["Monitoring"])
