"""Unit tests for the Final Report Generator."""

import pytest
from datetime import datetime, timezone, timedelta
from core.report_generator import ReportGenerator
from app.state import ForgeState

@pytest.fixture
def mock_state() -> ForgeState:
    """Provides a mocked ForgeState for testing the final report generator."""
    started = (datetime.now(timezone.utc) - timedelta(hours=2, minutes=30, seconds=15)).isoformat()
    # pyrefly: ignore [bad-typed-dict-key]
    return {
        "user_request": "Build an e-commerce app",
        "current_stage": "production_readiness",
        "approval_status": "approved",
        "approval_history": [{"stage": "solution_architecture", "decision": "approved"}],
        "requirements": "req docs",
        "architecture": "arch docs",
        "backend_blueprint": "backend docs",
        "implementation": "impl docs",
        "generated_files": {
            "src/main.py": "print('hello')",
            "src/utils.py": "def add(a, b): return a + b"
        },
        "qa_report": "qa...",
        "qa_score": 88,
        "security_report": "sec...",
        "security_score": 95,
        "review_report": "rev...",
        "review_score": 82,
        "overall_quality_score": 89,
        "quality_gate_status": "approved",
        "deployment_status": "READY FOR DEPLOYMENT",
        # pyrefly: ignore [bad-typed-dict-key]
        "deployment_emoji": "🟢",
        "artifacts": {
            "requirements": ["artifacts/requirements/requirements_v1.md"],
            "architecture": ["artifacts/architecture/architecture_v1.md"],
            "backend": ["artifacts/backend/backend_blueprint_v1.md"]
        },
        "messages": [
            type("MockMsg", (object,), {"name": "engineering_manager"})(),
            type("MockMsg", (object,), {"name": "qa_engineer"})(),
            type("MockMsg", (object,), {"name": "security_engineer"})(),
            type("MockMsg", (object,), {"name": "code_reviewer"})(),
        ],
        "metadata": {
            "started_at": started,
            "performance_score": "A+",
            "accessibility_score": "100"
        }
    }

def test_calculate_metrics(mock_state):
    """Test metrics calculation logic."""
    metrics = ReportGenerator.calculate_metrics(mock_state)
    
    assert metrics["generated_artifacts_count"] == 3
    assert metrics["generated_files_count"] == 2
    assert metrics["agents_executed"] == 4
    assert metrics["parallel_executions"] == 1
    assert metrics["approval_gates_completed"] == 2  # 1 in history + 1 quality gate
    
    # execution time should be approximately "2h 30m 15s"
    assert "2h 30m" in metrics["workflow_execution_time"]
    assert metrics["project_status"] == "🟢 READY FOR DEPLOYMENT"

def test_generate_report(mock_state):
    """Test generating the Markdown report."""
    report = ReportGenerator.generate(mock_state)
    
    assert "ForgeAI Final Report" in report
    assert "Requirements        ✅" in report
    assert "QA                  88/100" in report
    assert "Security            95/100" in report
    assert "Review              82/100" in report
    assert "Quality             89/100" in report
    
    # Check metrics section
    assert "• Number of generated files: 2" in report
    assert "• Number of artifacts generated: 3" in report
    assert "• Number of parallel executions: 1" in report
    
    # Check extensible metrics
    assert "Extended Metrics" in report
    assert "Performance Score: A+" in report

def test_missing_data_handling():
    """Test generator with minimal state (missing fields)."""
    # pyrefly: ignore [bad-typed-dict-key]
    minimal_state: ForgeState = {
        "user_request": "Basic",
        "current_stage": "end",
        "approval_status": "pending",
        "approval_history": [],
        "artifacts": {},
        "generated_files": {},
        "messages": [],
        "metadata": {}
    }
    
    metrics = ReportGenerator.calculate_metrics(minimal_state)
    assert metrics["workflow_execution_time"] == "N/A"
    assert metrics["project_status"] == "UNKNOWN"
    
    report = ReportGenerator.generate(minimal_state)
    assert "QA                  N/A" in report
    assert "Requirements        ❌" in report
    assert "Deployment          N/A" in report
    assert "Extended Metrics" not in report
