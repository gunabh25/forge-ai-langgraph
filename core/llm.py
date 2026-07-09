"""Factory for initializing configured LLM instances."""

from typing import Optional, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from app.settings import settings
from core.workflow_events import WorkflowEventManager, EventTypes

import time
import uuid
import core.context as ctx
from config.logging import get_logger

logger = get_logger("core.llm")

class ForgeCallbackHandler(BaseCallbackHandler):
    """Intercepts LLM executions to extract telemetry and tokens."""
    
    def __init__(self):
        super().__init__()
        self.run_start_times = {}
        self.request_tokens = {}
        
    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        """Called when LLM execution starts."""
        run_id = kwargs.get("run_id", uuid.uuid4())
        self.run_start_times[run_id] = time.time()
        
        request_id = str(uuid.uuid4())
        self.request_tokens[run_id] = ctx.request_id_var.set(request_id)
        
        model_name = serialized.get("kwargs", {}).get("model", "unknown-model") if serialized else "unknown-model"
        
        WorkflowEventManager().publish(EventTypes.LLM_STARTED, {
            "request_id": request_id,
            "provider": "google",  # Defaulting or could extract from serialized
            "model": model_name
        })
        logger.debug(f"LLM Started: {model_name}", extra={"event_type": EventTypes.LLM_STARTED})
        
    def on_llm_error(self, error: BaseException, **kwargs: Any) -> Any:
        """Called when LLM errors."""
        run_id = kwargs.get("run_id")
        start_time = self.run_start_times.pop(run_id, time.time())
        latency_ms = int((time.time() - start_time) * 1000)
        
        WorkflowEventManager().publish(EventTypes.LLM_COMPLETED, {
            "status": "failed",
            "error": str(error),
            "latency_ms": latency_ms
        })
        logger.error(f"LLM Failed ({latency_ms}ms): {error}", extra={"event_type": EventTypes.LLM_COMPLETED})
        
        # Pop request token
        if run_id in self.request_tokens:
            token = self.request_tokens.pop(run_id)
            token.var.reset(token)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM execution completes."""
        run_id = kwargs.get("run_id")
        start_time = self.run_start_times.pop(run_id, time.time())
        latency_ms = int((time.time() - start_time) * 1000)
        
        try:
            if not response.generations or not response.generations[0]:
                self._finish_run(run_id, latency_ms, status="empty")
                return
                
            generation = response.generations[0][0]
            message = getattr(generation, "message", None)
            
            reasoning = "Implicit reasoning extracted."
            if message and hasattr(message, "response_metadata"):
                metadata = message.response_metadata
                if "reasoning_tokens" in metadata:
                    reasoning = f"Explicit reasoning tokens: {metadata['reasoning_tokens']}"
                elif "prompt_feedback" in metadata:
                    reasoning = str(metadata["prompt_feedback"])
            
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
            
            token_usage = {}
            if message and hasattr(message, "response_metadata"):
                token_usage = message.response_metadata.get("token_usage", {})
                
            WorkflowEventManager().publish(
                EventTypes.LLM_COMPLETED,
                {
                    "status": "success",
                    "reasoning": reasoning,
                    "input_tokens": token_usage.get("prompt_token_count", 0),
                    "output_tokens": token_usage.get("candidates_token_count", 0),
                    "latency_ms": latency_ms
                }
            )
            logger.debug(f"LLM Completed in {latency_ms}ms", extra={"event_type": EventTypes.LLM_COMPLETED})
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
        finally:
            self._finish_run(run_id, latency_ms)
            
    def _finish_run(self, run_id, latency_ms, status="success"):
        if run_id in self.request_tokens:
            token = self.request_tokens.pop(run_id)
            token.var.reset(token)


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
