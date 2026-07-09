"""OpenAI LLM Provider implementation."""

from typing import Any, List
from langchain_core.messages import BaseMessage
from core.providers.base import BaseLLMProvider
from app.settings import settings

class OpenAIProvider(BaseLLMProvider):
    """
    Provider implementation for OpenAI's models (e.g., gpt-4o, gpt-4.1).
    Delegates generation to LangChain's ChatOpenAI.
    """

    def __init__(self, **kwargs: Any):
        try:
            from langchain_openai import ChatOpenAI  # type: ignore
        except ImportError as e:
            raise ImportError(
                "langchain-openai package is required for 'openai' provider. "
                "Install it using: pip install langchain-openai"
            ) from e

        self.model_name = kwargs.pop("model_name", settings.MODEL_NAME)
        self.temperature = kwargs.pop("temperature", settings.TEMPERATURE)
        self.max_tokens = kwargs.pop("max_tokens", settings.MAX_TOKENS)
        self.callbacks = kwargs.pop("callbacks", [])
        
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=settings.OPENAI_API_KEY,
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
        return "openai"
