"""Application settings management powered by Pydantic Settings."""

from typing import Optional, Dict
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from core.constants import ModelDefaults

class Settings(BaseSettings):
    """Configuration settings for the ForgeAI application, populated via environment variables and a .env file."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Keys and Provider Options
    GOOGLE_API_KEY: Optional[str] = None
    MODEL_NAME: str = ModelDefaults.GEMINI_MODEL
    TEMPERATURE: float = ModelDefaults.TEMPERATURE
    MAX_TOKENS: Optional[int] = ModelDefaults.MAX_TOKENS
    ARTIFACT_ROOT: str = "artifacts"
    ENABLE_TRACING: bool = False
    DEBUG: bool = False
    # When True, UML diagrams are generated one-at-a-time instead of in parallel.
    # Enable for free-tier Gemini plans (5 req/min rate limit).
    UML_SEQUENTIAL_GENERATION: bool = False
    # Maximum number of LLM-driven repair cycles per diagram before it is
    # permanently marked VALIDATION_FAILED and the workflow continues.
    # Override via MAX_UML_REPAIR_ATTEMPTS in your .env file.
    MAX_UML_REPAIR_ATTEMPTS: int = 2
    
    # AI Quality Optimization flags
    ENABLE_UML_REVIEW: bool = False
    ENABLE_FEW_SHOT: bool = False
    MIN_DIAGRAM_SCORE: int = 9

    # Multi-provider integrations
    LLM_PROVIDER: str = "google"  # google, openai, anthropic, ollama, openrouter
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: Optional[str] = "http://localhost:11434"
    OPENROUTER_API_KEY: Optional[str] = None

    # Quality Engine configuration
    QUALITY_WEIGHTS: Dict[str, float] = Field(
        default_factory=lambda: {"qa": 0.30, "security": 0.40, "review": 0.30}
    )
    QUALITY_THRESHOLDS: Dict[str, int] = Field(
        default_factory=lambda: {"ready": 90, "needs_improvement": 75}
    )

# Reusable settings instance
settings = Settings()
