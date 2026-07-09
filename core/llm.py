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


class LLMFactoryWrapper:
    """Legacy wrapper for backward compatibility, now delegating to providers architecture."""
    
    @staticmethod
    def create_llm(provider: Optional[str] = None, **kwargs: Any) -> Any:
        """Create and initialize an LLM provider instance."""
        # Add the observability callback
        callbacks = kwargs.pop("callbacks", [])
        callbacks.append(ForgeCallbackHandler())
        kwargs["callbacks"] = callbacks
        
        from core.providers.factory import LLMFactory
        return LLMFactory.create(provider=provider, **kwargs)

def get_llm(**kwargs: Any) -> Any:
    """Convenience helper to fetch the default configured LLM.
    
    Args:
        **kwargs: Overrides for configuration.
        
    Returns:
        BaseLLMProvider: An initialized LLM Provider (duck-types with LangChain BaseChatModel).
    """
    return LLMFactoryWrapper.create_llm(**kwargs)
