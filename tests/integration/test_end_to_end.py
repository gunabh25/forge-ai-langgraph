"""Integration test for end-to-end ForgeAI execution."""

import os
import pytest
from unittest.mock import patch, MagicMock
from app.workflow import ForgeWorkflow
from core.approval import AutoApproval, AutoQualityGate
from app.settings import settings

@pytest.fixture
def mock_all_agent_llms():
    """Mocks all LLM instances for the agents."""
    with patch("core.llm.LLMFactory.create_llm") as mock_create_llm:
        mock_llm = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = '{"src/main.py": "print(\'hello\')"}'  # Return non-empty JSON object
        mock_llm.invoke.return_value = mock_msg
        mock_create_llm.return_value = mock_llm
        yield mock_create_llm

def test_full_workflow_execution(mock_all_agent_llms):
    """Verify entire workflow from Engineering Manager to Final Report."""
    
    # Configure auto approvals
    workflow = ForgeWorkflow(
        approval_interface=AutoApproval(),
        quality_gate_interface=AutoQualityGate()
    )
    
    # Use a small test request
    request = "Build a simple hello world API with FastAPI."
    
    final_state = workflow.execute(request)
        
    print(f"Artifacts: {final_state.get('artifacts')}")
    # 1. Verify stages completed
    assert final_state.get("current_stage") == "final_report_generation"
    
    # 2. Verify state updates and artifacts
    assert "requirements" in final_state
    assert "architecture" in final_state
    assert "backend_blueprint" in final_state
    assert "implementation" in final_state
    
    # 3. Verify approvals were automatically granted
    history = final_state.get("approval_history", [])
    assert len(history) > 0
    from core.constants import ApprovalStatuses
    assert history[0]["decision"] == ApprovalStatuses.APPROVED
    
    # 4. Verify Final Report
    assert "reports" in final_state.get("artifacts", {})
