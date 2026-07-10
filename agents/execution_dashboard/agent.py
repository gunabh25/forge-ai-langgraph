"""Execution Dashboard Agent implementation."""

import json
from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from agents.base import BaseAgent
from core.agent_registry import AgentRegistry
from app.state import ForgeState
from config.logging import get_logger
from core.utils import generate_timestamp

logger = get_logger("agents.execution_dashboard")

class ExecutionDashboardAgent(BaseAgent):
    """Generates the final workflow execution summary."""
    
    @property
    def name(self) -> str:
        return "Execution Dashboard Agent"
        
    @property
    def description(self) -> str:
        return "Aggregates execution states into a final summary report."
        
    @property
    def capabilities(self) -> List[str]:
        return ["workflow_summary", "metrics_aggregation"]

    @property
    def requires(self) -> List[str]:
        return ["diagram_execution_states"]

    @property
    def produces(self) -> List[str]:
        return ["workflow_execution_summary"]

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Dashboard Agent."""
        logger.info("Execution Dashboard Agent starting execution.")
        
        diagram_states = state.get("diagram_execution_states", {})
        
        total_diagrams = len(diagram_states)
        success_count = sum(1 for s in diagram_states.values() if s.get("status") in ("rendered", "UNCHANGED"))
        failed_count = total_diagrams - success_count
        
        total_execution_time_ms = sum(s.get("execution_time_ms", 0) for s in diagram_states.values() if s.get("status") != "UNCHANGED")
        total_llm_calls = sum(s.get("llm_calls", 0) for s in diagram_states.values() if s.get("status") != "UNCHANGED")
        
        previous_states = state.get("previous_diagram_execution_states") or {}
        
        reused_artifacts = 0
        updated_artifacts = 0
        new_artifacts = 0
        removed_artifacts = 0
        saved_llm_calls = 0
        saved_latency_ms = 0
        
        repaired_successfully = 0
        permanently_failed = 0
        total_repair_attempts = 0
        
        for diag_id, s in diagram_states.items():
            attempt = s.get("attempt", 1)
            status = s.get("status")
            
            if attempt > 1:
                total_repair_attempts += (attempt - 1)
                if status == "rendered":
                    repaired_successfully += 1
            if status == "failed_validation":
                permanently_failed += 1
                
            if status == "UNCHANGED":
                reused_artifacts += 1
                saved_llm_calls += s.get("llm_calls", 0)
                saved_latency_ms += s.get("execution_time_ms", 0)
            else:
                if diag_id in previous_states:
                    updated_artifacts += 1
                else:
                    new_artifacts += 1
                    
        for old_id in previous_states:
            if old_id not in diagram_states:
                removed_artifacts += 1
        
        details = []
        for diag_id, s in diagram_states.items():
            details.append({
                "diagram_id": diag_id,
                "type": s.get("diagram_type", "unknown"),
                "status": s.get("status"),
                "attempt": s.get("attempt", 0),
                "execution_time_ms": s.get("execution_time_ms", 0),
                "llm_calls": s.get("llm_calls", 0)
            })
            
        total_failed_needing_repair = repaired_successfully + permanently_failed
        repair_success_rate = f"{(repaired_successfully / total_failed_needing_repair * 100):.1f}%" if total_failed_needing_repair > 0 else "N/A"
        
        summary = {
            "total_diagrams": total_diagrams,
            "successful_diagrams": success_count,
            "failed_diagrams": failed_count,
            "success_rate": f"{(success_count / total_diagrams * 100) if total_diagrams > 0 else 0:.1f}%",
            "total_execution_time_ms": total_execution_time_ms,
            "total_llm_calls": total_llm_calls,
            "reused_artifacts": reused_artifacts,
            "updated_artifacts": updated_artifacts,
            "new_artifacts": new_artifacts,
            "removed_artifacts": removed_artifacts,
            "saved_llm_calls": saved_llm_calls,
            "saved_latency_ms": saved_latency_ms,
            "repaired_successfully": repaired_successfully,
            "permanently_failed": permanently_failed,
            "total_repair_attempts": total_repair_attempts,
            "repair_success_rate": repair_success_rate,
            "diagram_details": details
        }
        
        logger.info(f"Dashboard Summary generated: {json.dumps(summary, indent=2)}")
        
        new_message = AIMessage(
            content=f"Workflow Execution Summary:\n{json.dumps(summary, indent=2)}",
            name="execution_dashboard"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "dashboard_completed": True,
            "last_updated": generate_timestamp()
        }
        
        return {
            "workflow_execution_summary": summary,
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "execution_dashboard"
        }

# Automatically register the agent
AgentRegistry().register(ExecutionDashboardAgent())
