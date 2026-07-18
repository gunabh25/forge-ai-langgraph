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
_SUCCESS_STATUSES = frozenset({"rendered", "success", "repaired", "UNCHANGED"})
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

        for diag_id, raw_s in diagram_states.items():
            s = raw_s or {}
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

            metrics = s.get("uml_validation_metrics") or {}
            diag_score = s.get("diagram_score")
            if diag_score is None:
                diag_score = metrics.get("diagram_score", 100.0)

            is_prod_ready = s.get("is_production_ready")
            if is_prod_ready is None:
                is_prod_ready = metrics.get("is_production_ready", True)

            score_card = s.get("score_card") or metrics.get("score_card")

            grammar_st = s.get("grammar_status", "passed")
            if grammar_st == "passed":
                grammar_display = "✓ Passed"
            elif grammar_st in ("timed_out", "warning"):
                grammar_display = "⚠ Timed Out"
            else:
                grammar_display = "✗ Failed"

            # Task 6 — rich per-diagram row
            details.append({
                "diagram_id": diag_id,
                "type": s.get("diagram_type", "unknown"),
                "status": status,
                "grammar_status": grammar_st,
                "grammar_display": grammar_display,
                "repair_attempts": repair_attempts,
                "failure_reason": failure_reason,
                "llm_calls": llm_calls,
                "execution_time_ms": exec_time,
                "diagram_score": diag_score,
                "is_production_ready": is_prod_ready,
                "score_card": score_card,
            })

        for old_id in previous_states:
            if old_id not in diagram_states:
                removed_artifacts += 1

        scores = [d.get("diagram_score", 100.0) for d in details if d.get("diagram_score") is not None]
        avg_score = round(sum(scores) / float(len(scores)), 1) if scores else 100.0
        # Derive production-ready count directly from score threshold for consistency
        prod_ready_count = sum(1 for d in details if float(d.get("diagram_score", 0)) >= 90.0)

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

        # Task 7 & 8 — Execution Summary with Cost Optimization metrics
        agent_cost_metrics = (state.get("metadata", {}) or {}).get("agent_cost_metrics", {})
        
        total_estimated_cost = 0.0
        total_cache_hits = 0
        total_llm_calls_new = 0
        
        # We need to estimate savings. If everything wasn't cached/skipped, what would it cost?
        # A simple approximation: if we saved X calls, we assume average cost per call.
        for agent_name, m in agent_cost_metrics.items():
            total_estimated_cost += m.get("estimated_cost", 0.0)
            total_cache_hits += m.get("cache_hits", 0)
            total_llm_calls_new += m.get("calls", 0)
            
        avg_cost_per_call = (total_estimated_cost / total_llm_calls_new) if total_llm_calls_new > 0 else 0.0
        
        # Saved calls based on cache hits + saved_llm_calls (from unchanged diagrams)
        total_saved_calls = total_cache_hits + saved_llm_calls
        estimated_cost_saved = total_saved_calls * avg_cost_per_call
        savings_pct = (estimated_cost_saved / (total_estimated_cost + estimated_cost_saved) * 100) if (total_estimated_cost + estimated_cost_saved) > 0 else 0.0

        summary: Dict[str, Any] = {
            "total_diagrams": total_diagrams,
            "successful_diagrams": success_count,
            "failed_diagrams": failed_count,
            "success_rate": f"{(success_count / total_diagrams * 100) if total_diagrams > 0 else 0:.1f}%",
            "average_diagram_score": avg_score,
            "production_ready_diagrams": f"{prod_ready_count}/{total_diagrams}",
            "total_execution_time_ms": total_execution_time_ms,
            "total_llm_calls": total_llm_calls_new,
            "total_llm_calls_saved": total_saved_calls,
            "total_cache_hits": total_cache_hits,
            "total_estimated_cost": total_estimated_cost,
            "total_estimated_cost_saved": estimated_cost_saved,
            "savings_pct": f"{savings_pct:.1f}%",
            # Incremental-update fields
            "reused_artifacts": reused_artifacts,
            "updated_artifacts": updated_artifacts,
            "new_artifacts": new_artifacts,
            "removed_artifacts": removed_artifacts,
            # Repair metrics
            "repaired_successfully": repaired_successfully,
            "permanently_failed": permanently_failed,
            "total_repair_attempts": total_repair_attempts,
            "repair_success_rate": repair_success_rate,
            "repair_success_rate_pct": uml_repair_metrics.get("repair_success_rate", "N/A"),
            "validation_failures": uml_repair_metrics.get("validation_failures", permanently_failed),
            "repair_failures": uml_repair_metrics.get("repair_failures", permanently_failed),
            "average_repairs_per_diagram": uml_repair_metrics.get("average_repairs_per_diagram", 0.0),
            # Detailed metrics
            "agent_cost_metrics": agent_cost_metrics,
            "diagram_details": details,
        }

        dashboard_text = (
            "----------------------------------------------------\n"
            f"Average Diagram Score: {avg_score} (Production Ready: {prod_ready_count}/{total_diagrams})\n"
            f"Total LLM Calls: {total_llm_calls_new}\n"
            f"LLM Calls Saved: {total_saved_calls}\n"
            f"Cache Hits: {total_cache_hits}\n"
            f"Estimated Cost: ${total_estimated_cost:.4f}\n"
            f"Estimated Savings: {savings_pct:.1f}%\n"
            "----------------------------------------------------\n"
            f"{json.dumps(summary, indent=2)}"
        )

        logger.info("Dashboard Summary:\n%s", dashboard_text)

        new_message = AIMessage(
            content=f"Workflow Execution Summary:\n{dashboard_text}",
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
