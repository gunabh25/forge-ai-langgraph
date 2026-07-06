"""Factory for initializing configured LLM instances."""

from typing import Optional, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from app.settings import settings
from core.workflow_events import WorkflowEventManager, EventTypes

class ForgeCallbackHandler(BaseCallbackHandler):
    """Intercepts LLM executions to extract explainability reasoning and token metrics."""
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM execution completes."""
        try:
            if not response.generations or not response.generations[0]:
                return
                
            generation = response.generations[0][0]
            message = getattr(generation, "message", None)
            
            # Extract reasoning (often in response_metadata or implicit in first paragraphs)
            reasoning = "Implicit reasoning extracted."
            if message and hasattr(message, "response_metadata"):
                # Try to extract explicit reasoning tokens (e.g. from newer models)
                metadata = message.response_metadata
                if "reasoning_tokens" in metadata:
                    reasoning = f"Explicit reasoning tokens: {metadata['reasoning_tokens']}"
                elif "prompt_feedback" in metadata:
                    reasoning = str(metadata["prompt_feedback"])
            
            # Fallback for implicit reasoning (first few lines of output)
            if reasoning == "Implicit reasoning extracted." and message and hasattr(message, "content"):
                lines = message.content.split("\n")
                reasoning_lines = []
                for line in lines:
                    if line.strip() and not line.startswith("```") and not line.startswith("#"):
                        reasoning_lines.append(line)
                    if len(reasoning_lines) > 3:
                        break
                if reasoning_lines:
                    reasoning = "\n".join(reasoning_lines)
            
            # Extract token usage
            token_usage = {}
            if message and hasattr(message, "response_metadata"):
                token_usage = message.response_metadata.get("token_usage", {})
                
            WorkflowEventManager().publish(
                EventTypes.LLM_COMPLETED,
                {
                    "reasoning": reasoning,
                    "token_usage": token_usage
                }
            )
        except Exception as e:
            pass


class LLMFactory:
    """Factory to build and return LangChain ChatModel instances based on application configuration."""
    
    @staticmethod
    def create_llm(provider: Optional[str] = None, **kwargs: Any) -> BaseChatModel:
        """Create and initialize a LangChain BaseChatModel instance."""
        provider = provider or settings.LLM_PROVIDER
        
        model_name = kwargs.pop("model_name", settings.MODEL_NAME)
        temperature = kwargs.pop("temperature", settings.TEMPERATURE)
        max_tokens = kwargs.pop("max_tokens", settings.MAX_TOKENS)
        
        # Add the observability callback
        callbacks = kwargs.pop("callbacks", [])
        callbacks.append(ForgeCallbackHandler())
        kwargs["callbacks"] = callbacks
        
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
