"""Factory for creating LLM providers."""

from typing import Any, Optional
from core.providers.base import BaseLLMProvider
from app.settings import settings

class LLMFactory:
    """
    Factory class responsible for instantiating the correct LLM provider
    based on application configuration (e.g., environment variables).
    """

    @staticmethod
    def create(provider: Optional[str] = None, **kwargs: Any) -> BaseLLMProvider:
        """
        Create and return an initialized BaseLLMProvider instance.
        
        Args:
            provider: Optional provider override (defaults to settings.LLM_PROVIDER)
            **kwargs: Configuration overrides for the provider
            
        Returns:
            An instance of a class that implements BaseLLMProvider.
        """
        provider = provider or settings.LLM_PROVIDER

        if provider == "google":
            from core.providers.gemini import GeminiProvider
            return GeminiProvider(**kwargs)
            
        elif provider == "openai":
            from core.providers.openai import OpenAIProvider
            return OpenAIProvider(**kwargs)
        
        # The architecture naturally extends to other providers like Anthropic,
        # Ollama, OpenRouter by adding the corresponding classes here.
        else:
            raise ValueError(
                f"Unsupported LLM provider: '{provider}'. "
                f"Please ensure LLM_PROVIDER is set to a supported value (e.g., 'google', 'openai')."
            )
