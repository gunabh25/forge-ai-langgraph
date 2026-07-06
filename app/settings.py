"""Application settings management powered by Pydantic Settings."""

from typing import Optional
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

    # Multi-provider integrations
    LLM_PROVIDER: str = "google"  # google, openai, anthropic, ollama, groq, openrouter
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: Optional[str] = "http://localhost:11434"
    GROQ_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

# Reusable settings instance
settings = Settings()
