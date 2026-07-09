"""Abstract Base Class for LLM Providers."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

class BaseLLMProvider(ABC):
    """
    Abstract interface that every LLM provider must implement.
    This ensures that the ForgeAI platform (agents, orchestrator, planners)
    remains completely agnostic of the underlying AI provider.
    """

    @abstractmethod
    def invoke(self, messages: List[BaseMessage], **kwargs: Any) -> Any:
        """
        Synchronous invocation of the LLM.
        
        Args:
            messages: A list of LangChain BaseMessage objects (SystemMessage, HumanMessage, etc.).
            **kwargs: Additional provider-specific kwargs.
            
        Returns:
            Any object that conforms to the expected response (e.g., AIMessage) 
            so that `response.content` remains compatible with existing agents.
        """
        pass

    @abstractmethod
    def stream(self, messages: List[BaseMessage], **kwargs: Any) -> Any:
        """
        Stream output from the LLM.
        
        Args:
            messages: A list of LangChain BaseMessage objects.
            **kwargs: Additional provider-specific kwargs.
            
        Returns:
            An iterator over message chunks.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Return the name of the model being used by this provider instance.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Return the identifier for this provider (e.g., "gemini", "openai").
        """
        pass
