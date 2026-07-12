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

# Statuses that count as successfully completed diagrams.
_SUCCESS_STATUSES = frozenset({"rendered", "success", "UNCHANGED"})
# Statuses that indicate the diagram was repaired before succeeding.
_REPAIRED_STATUSES = frozenset({"repaired"})
# Terminal failure statuses.
_FAILED_STATUSES = frozenset({"VALIDATION_FAILED", "failed_render", "failed_validation", "RATE_LIMITED"})


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

        diagram_states = state.get("diagram_execution_states", {}) or {}
        previous_states = state.get("previous_diagram_execution_states") or {}

        total_diagrams = len(diagram_states)

        # Counters
        success_count = 0
        failed_count = 0
        repaired_successfully = 0
        permanently_failed = 0
        total_repair_attempts = 0
        total_execution_time_ms = 0
        total_llm_calls = 0

        # Incremental-update counters
        reused_artifacts = 0
        updated_artifacts = 0
        new_artifacts = 0
        removed_artifacts = 0
        saved_llm_calls = 0
        saved_latency_ms = 0

        # Per-diagram detail rows (Task 6 — extended fields)
        details: List[Dict[str, Any]] = []

        for diag_id, s in diagram_states.items():
            status = s.get("status", "unknown")
            repair_attempts = s.get("repair_attempts", 0)
            failure_reason = s.get("failure_reason")
            exec_time = s.get("execution_time_ms", 0)
            llm_calls = s.get("llm_calls", 0)

            # Aggregate totals (exclude UNCHANGED from time/cost — it was free)
            if status != "UNCHANGED":
                total_execution_time_ms += exec_time
                total_llm_calls += llm_calls

            if status in _SUCCESS_STATUSES:
                success_count += 1
                if repair_attempts > 0 and status != "UNCHANGED":
                    repaired_successfully += 1
            elif status in _FAILED_STATUSES:
                failed_count += 1
                if status == "VALIDATION_FAILED":
                    permanently_failed += 1

            total_repair_attempts += repair_attempts

            # Incremental-update accounting
            if status == "UNCHANGED":
                reused_artifacts += 1
                saved_llm_calls += llm_calls
                saved_latency_ms += exec_time
            else:
                if diag_id in previous_states:
                    updated_artifacts += 1
                else:
                    new_artifacts += 1

            # Task 6 — rich per-diagram row
            details.append({
                "diagram_id": diag_id,
                "type": s.get("diagram_type", "unknown"),
                "status": status,
                "repair_attempts": repair_attempts,
                "failure_reason": failure_reason,
                "llm_calls": llm_calls,
                "execution_time_ms": exec_time,
            })

        for old_id in previous_states:
            if old_id not in diagram_states:
                removed_artifacts += 1

        total_failed_needing_repair = repaired_successfully + permanently_failed
        repair_success_rate = (
            f"{(repaired_successfully / total_failed_needing_repair * 100):.1f}%"
            if total_failed_needing_repair > 0
            else "N/A"
        )

        # Pull extended metrics produced by the validator (Task 4).
        uml_repair_metrics: Dict[str, Any] = (
            state.get("metadata", {}) or {}
        ).get("uml_repair_metrics", {})

        summary: Dict[str, Any] = {
            "total_diagrams": total_diagrams,
            "successful_diagrams": success_count,
            "failed_diagrams": failed_count,
            "success_rate": f"{(success_count / total_diagrams * 100) if total_diagrams > 0 else 0:.1f}%",
            "total_execution_time_ms": total_execution_time_ms,
            "total_llm_calls": total_llm_calls,
            # Incremental-update fields
            "reused_artifacts": reused_artifacts,
            "updated_artifacts": updated_artifacts,
            "new_artifacts": new_artifacts,
            "removed_artifacts": removed_artifacts,
            "saved_llm_calls": saved_llm_calls,
            "saved_latency_ms": saved_latency_ms,
            # Repair metrics
            "repaired_successfully": repaired_successfully,
            "permanently_failed": permanently_failed,
            "total_repair_attempts": total_repair_attempts,
            "repair_success_rate": repair_success_rate,
            # Extended repair metrics from validator (Task 4)
            "repair_success_rate_pct": uml_repair_metrics.get("repair_success_rate", "N/A"),
            "validation_failures": uml_repair_metrics.get("validation_failures", permanently_failed),
            "repair_failures": uml_repair_metrics.get("repair_failures", permanently_failed),
            "average_repairs_per_diagram": uml_repair_metrics.get("average_repairs_per_diagram", 0.0),
            # Task 6 — detailed per-diagram table
            "diagram_details": details,
        }

        logger.info("Dashboard Summary:\n%s", json.dumps(summary, indent=2))

        new_message = AIMessage(
            content=f"Workflow Execution Summary:\n{json.dumps(summary, indent=2)}",
            name="execution_dashboard",
        )

        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "dashboard_completed": True,
            "last_updated": generate_timestamp(),
        }

        return {
            "workflow_execution_summary": summary,
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "execution_dashboard",
        }


# Automatically register the agent
AgentRegistry().register(ExecutionDashboardAgent())
