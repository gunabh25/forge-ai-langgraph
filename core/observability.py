"""Observability helper for tracking agent executions."""

import time
import uuid
from typing import Dict, Any, Optional
from core.workflow_events import WorkflowEventManager, EventTypes
from app.state import ForgeState

class ExecutionObserver:
    """Context manager and helper for wrapping agent executions to collect observability metrics."""
    
    def __init__(self, agent_name: str, state: ForgeState):
        self.agent_name = agent_name
        self.state = state
        self.start_time: float = 0.0
        self.llm_calls: int = 0
        self.artifacts_before: set = set()
        self.event_manager = WorkflowEventManager()
        
    def _on_llm_completed(self, payload: dict) -> None:
        """Callback to track LLM invocations."""
        self.llm_calls += 1
        
    def __enter__(self):
        """Start tracking metrics."""
        self.start_time = time.time()
        
        # Snapshot artifacts before execution
        for paths in self.state.get("artifacts", {}).values():
            self.artifacts_before.update(paths)
            
        self.event_manager.subscribe(EventTypes.LLM_COMPLETED, self._on_llm_completed)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up subscriptions."""
        self.event_manager.unsubscribe(EventTypes.LLM_COMPLETED, self._on_llm_completed)
        
    def finalize(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize the execution and append the structured metadata to the result."""
        end_time = time.time()
        latency_ms = int((end_time - self.start_time) * 1000)
        
        # Calculate generated artifacts
        artifacts_after = set()
        for paths in result.get("artifacts", {}).values():
            artifacts_after.update(paths)
        generated_artifacts = list(artifacts_after - self.artifacts_before)
        
        # Check if execution ID already exists in state, if not generate one
        exec_report = self.state.get("execution_report") or {}
        execution_id = exec_report.get("execution_id") or str(uuid.uuid4())
        
        # Retrieve retry count from metadata if available
        metadata = self.state.get("metadata") or {}
        retry_count = metadata.get("retry_count", 0)
        
        # Extract reasoning from result if returned
        reasoning = result.get("reasoning_logs", [])
        
        execution_data = {
            "agent": self.agent_name,
            "latency_ms": latency_ms,
            "llm_calls": self.llm_calls,
            "retry_count": retry_count,
            "generated_artifacts": generated_artifacts,
            "reasoning": reasoning,
            "cost_estimate": 0.0,  # Placeholder for future token-based estimation
            "execution_timeline": [
                {"event": "started", "timestamp": self.start_time},
                {"event": "completed", "timestamp": end_time}
            ]
        }
        
        # Initialize execution_report dictionary if not present in the result
        if "execution_report" not in result:
            result["execution_report"] = {}
            
        result["execution_report"]["execution_id"] = execution_id
        
        if "executions" not in result["execution_report"]:
            result["execution_report"]["executions"] = []
            
        result["execution_report"]["executions"].append(execution_data)
        
        return result
