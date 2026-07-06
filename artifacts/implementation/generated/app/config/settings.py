"""
Application settings and configuration for the POS system.

This module defines the `Settings` class using Pydantic's `BaseSettings`
to manage environment variables and application configurations.
It ensures that all necessary settings are loaded and validated
at application startup, providing a single source of truth for configuration.
"""

from typing import List, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn, AmqpDsn, HttpUrl, SecretStr


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Settings are loaded from `.env` file (if present) and environment variables.
    Pydantic's `BaseSettings` handles parsing and validation.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = Field("POS System Backend", description="Name of the application")
    APP_VERSION: str = Field("1.0.0", description="Version of the application")
    ENVIRONMENT: Literal["development", "testing", "production"] = Field(
        "development", description="Application environment"
    )
    DEBUG: bool = Field(True, description="Enable debug mode")

    # Database Settings
    DATABASE_URL: PostgresDsn = Field(
        ...,
        description="PostgreSQL database connection URL (e.g., postgresql://user:pass@host:port/db)",
    )
    DATABASE_POOL_SIZE: int = Field(
        10, description="Number of connections to keep open in the database pool"
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        20, description="Maximum number of connections to allow beyond the pool size"
    )

    # JWT Authentication Settings
    JWT_SECRET_KEY: SecretStr = Field(
        ..., description="Secret key for signing JWT tokens"
    )
    JWT_ALGORITHM: str = Field("HS256", description="Algorithm used for JWT signing")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        30, description="Access token expiration time in minutes"
    )

    # Redis Cache Settings
    REDIS_URL: RedisDsn = Field(
        "redis://localhost:6379/0", description="Redis connection URL"
    )
    REDIS_CACHE_TTL_SECONDS: int = Field(
        3600, description="Default TTL for cached items in seconds (1 hour)"
    )

    # RabbitMQ Messaging Settings
    RABBITMQ_URL: AmqpDsn = Field(
        "amqp://guest:guest@localhost:5672/", description="RabbitMQ connection URL"
    )
    RABBITMQ_QUEUE_SALES_EVENTS: str = Field(
        "sales_events", description="Queue name for sales events"
    )
    RABBITMQ_QUEUE_INVENTORY_EVENTS: str = Field(
        "inventory_events", description="Queue name for inventory events"
    )
    RABBITMQ_QUEUE_TRANSFER_EVENTS: str = Field(
        "transfer_events", description="Queue name for transfer events"
    )
    RABBITMQ_QUEUE_SYNC_OFFLINE: str = Field(
        "sync_offline_transactions", description="Queue name for offline transaction sync"
    )

    # AWS S3 Storage Settings (for receipts, audit logs)
    AWS_ACCESS_KEY_ID: SecretStr = Field(
        ..., description="AWS Access Key ID for S3 access"
    )
    AWS_SECRET_ACCESS_KEY: SecretStr = Field(
        ..., description="AWS Secret Access Key for S3 access"
    )
    AWS_REGION_NAME: str = Field("us-east-1", description="AWS region for S3 bucket")
    S3_RECEIPT_BUCKET_NAME: str = Field(
        ..., description="S3 bucket name for storing sales receipts"
    )
    S3_AUDIT_LOG_BUCKET_NAME: str = Field(
        ..., description="S3 bucket name for storing audit logs"
    )

    # External Service Integrations (placeholders for now)
    PAYMENT_GATEWAY_API_URL: HttpUrl | None = Field(
        None, description="URL for the payment gateway API"
    )
    PAYMENT_GATEWAY_API_KEY: SecretStr | None = Field(
        None, description="API key for the payment gateway"
    )
    TAX_CALCULATION_API_URL: HttpUrl | None = Field(
        None, description="URL for the tax calculation API"
    )
    TAX_CALCULATION_API_KEY: SecretStr | None = Field(
        None, description="API key for the tax calculation service"
    )

    # Logging Settings
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", description="Minimum logging level"
    )
    LOG_FORMAT: str = Field(
        "%(levelname)s:%(name)s:%(message)s", description="Logging format string"
    )

    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        ["*"], description="List of allowed origins for CORS"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        True, description="Allow credentials for CORS requests"
    )
    CORS_ALLOW_METHODS: List[str] = Field(
        ["*"], description="List of allowed HTTP methods for CORS"
    )
    CORS_ALLOW_HEADERS: List[str] = Field(
        ["*"], description="List of allowed HTTP headers for CORS"
    )


# Create a singleton instance of the settings
settings = Settings()