"""Regression test suite for execution dashboard summary metrics aggregation."""

from agents.execution_dashboard.agent import ExecutionDashboardAgent
from core.workflow_events import EventTypes


def test_dashboard_agent_aggregates_repaired_status_correctly():
    """Verify ExecutionDashboardAgent counts repaired diagrams as successful and production ready."""
    agent = ExecutionDashboardAgent()
    state = {
        "diagram_execution_states": {
            "component": {
                "status": "success",
                "repair_attempts": 0,
                "diagram_score": 100.0,
                "is_production_ready": True,
                "execution_time_ms": 1200,
                "llm_calls": 1
            },
            "sequence": {
                "status": "repaired",
                "repair_attempts": 2,
                "diagram_score": 95.0,
                "is_production_ready": True,
                "execution_time_ms": 3400,
                "llm_calls": 3
            }
        }
    }

    res = agent.run(state)
    summary = res["workflow_execution_summary"]

    assert summary["successful_diagrams"] == 2
    assert summary["failed_diagrams"] == 0
    assert summary["total_repair_attempts"] == 2
    assert summary["repaired_successfully"] == 1
    assert summary["production_ready_diagrams"] == "2/2"
    assert summary["average_diagram_score"] == 97.5
