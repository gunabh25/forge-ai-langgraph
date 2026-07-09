"""Gemini LLM Provider implementation."""

from typing import Any, List, Optional
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from core.providers.base import BaseLLMProvider
from app.settings import settings

class GeminiProvider(BaseLLMProvider):
    """
    Provider implementation for Google's Gemini models.
    Delegates generation to LangChain's ChatGoogleGenerativeAI.
    """

    def __init__(self, **kwargs: Any):
        self.model_name = kwargs.pop("model_name", settings.MODEL_NAME)
        self.temperature = kwargs.pop("temperature", settings.TEMPERATURE)
        self.max_tokens = kwargs.pop("max_tokens", settings.MAX_TOKENS)
        self.callbacks = kwargs.pop("callbacks", [])
        
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            google_api_key=settings.GOOGLE_API_KEY,
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
        return "gemini"
