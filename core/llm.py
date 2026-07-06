"""Factory for initializing configured LLM instances."""

from typing import Optional, Any
from langchain_core.language_models.chat_models import BaseChatModel
from app.settings import settings

class LLMFactory:
    """Factory to build and return LangChain ChatModel instances based on application configuration."""
    
    @staticmethod
    def create_llm(provider: Optional[str] = None, **kwargs: Any) -> BaseChatModel:
        """Create and initialize a LangChain BaseChatModel instance.
        
        Args:
            provider: LLM provider string. Defaults to settings.LLM_PROVIDER.
            **kwargs: Overrides for configuration arguments (model_name, temperature, etc.).
            
        Returns:
            An initialized ChatModel instance.
            
        Raises:
            ValueError: If an unsupported LLM provider is specified.
            ImportError: If the client library for the specified provider is not installed.
        """
        provider = provider or settings.LLM_PROVIDER
        
        model_name = kwargs.pop("model_name", settings.MODEL_NAME)
        temperature = kwargs.pop("temperature", settings.TEMPERATURE)
        max_tokens = kwargs.pop("max_tokens", settings.MAX_TOKENS)
        
        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = settings.GOOGLE_API_KEY
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_output_tokens=max_tokens,
                google_api_key=api_key,
                **kwargs
            )
            
        elif provider == "openai":
            try:
                from langchain_openai import ChatOpenAI  # type: ignore
            except ImportError as e:
                raise ImportError(
                    "langchain-openai package is required for 'openai' provider. "
                    "Install it using: pip install langchain-openai"
                ) from e
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=settings.OPENAI_API_KEY,
                **kwargs
            )
            
        elif provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic  # type: ignore
            except ImportError as e:
                raise ImportError(
                    "langchain-anthropic package is required for 'anthropic' provider. "
                    "Install it using: pip install langchain-anthropic"
                ) from e
            return ChatAnthropic(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=settings.ANTHROPIC_API_KEY,
                **kwargs
            )
            
        elif provider == "ollama":
            try:
                from langchain_community.chat_models import ChatOllama  # type: ignore
            except ImportError as e:
                raise ImportError(
                    "langchain-community package is required for 'ollama' provider. "
                    "Install it using: pip install langchain-community"
                ) from e
            return ChatOllama(
                model=model_name,
                temperature=temperature,
                base_url=settings.OLLAMA_BASE_URL,
                **kwargs
            )
            
        elif provider == "groq":
            try:
                from langchain_groq import ChatGroq  # type: ignore
            except ImportError as e:
                raise ImportError(
                    "langchain-groq package is required for 'groq' provider. "
                    "Install it using: pip install langchain-groq"
                ) from e
            return ChatGroq(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=settings.GROQ_API_KEY,
                **kwargs
            )
            
        elif provider == "openrouter":
            try:
                from langchain_openai import ChatOpenAI  # type: ignore
            except ImportError as e:
                raise ImportError(
                    "langchain-openai package is required for 'openrouter' provider. "
                    "Install it using: pip install langchain-openai"
                ) from e
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                **kwargs
            )
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

def get_llm(**kwargs: Any) -> BaseChatModel:
    """Convenience helper to fetch the default configured LLM.
    
    Args:
        **kwargs: Overrides for configuration.
        
    Returns:
        BaseChatModel: An initialized ChatModel.
    """
    return LLMFactory.create_llm(**kwargs)
