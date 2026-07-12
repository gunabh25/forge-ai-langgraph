"""Groq LLM Provider implementation."""

from typing import Any, List
from langchain_core.messages import BaseMessage
from core.providers.base import BaseLLMProvider
from app.settings import settings

class GroqProvider(BaseLLMProvider):
    """
    Provider implementation for Groq's models (e.g., llama3-8b-8192).
    Delegates generation to LangChain's ChatGroq.
    """

    def __init__(self, **kwargs: Any):
        try:
            from langchain_groq import ChatGroq  # type: ignore
        except ImportError as e:
            raise ImportError(
                "langchain-groq package is required for 'groq' provider. "
                "Install it using: pip install langchain-groq"
            ) from e

        self.model_name = kwargs.pop("model_name", settings.GROQ_MODEL or "llama3-8b-8192")
        self.temperature = kwargs.pop("temperature", settings.TEMPERATURE)
        self.max_tokens = kwargs.pop("max_tokens", settings.MAX_TOKENS)
        self.callbacks = kwargs.pop("callbacks", [])
        
        self.llm = ChatGroq(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=settings.GROQ_API_KEY,
            callbacks=self.callbacks,
            **kwargs
        )

    def invoke(self, messages: List[BaseMessage], **kwargs: Any) -> Any:
        return self.llm.invoke(messages, **kwargs)

    def stream(self, messages: List[BaseMessage], **kwargs: Any) -> Any:
        return self.llm.stream(messages, **kwargs)

    def get_model_name(self) -> str:
        return self.model_name

    def get_provider_name(self) -> str:
        return "groq"