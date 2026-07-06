"""Unit and integration tests for the RequirementAnalystAgent and workflow integration."""

import os
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from agents.requirement_analyst.agent import RequirementAnalystAgent
from app.state import ForgeState
from app.workflow import ForgeWorkflow
from core.constants import WorkflowStages, ApprovalStatuses
from core.artifact_manager import ArtifactManager

@pytest.fixture
def temp_artifact_dir(tmp_path):
    """Fixture to provide a clean temporary directory for artifact testing."""
    return str(tmp_path)

@pytest.fixture
def mock_llm_responses():
    """Mock the LLMs for both EM and RA agents."""
    with patch("agents.engineering_manager.agent.get_llm") as mock_em_llm, \
         patch("agents.requirement_analyst.agent.get_llm") as mock_ra_llm:
         
        # Mock EM response
        em_instance = MagicMock()
        em_instance.invoke.return_value = AIMessage(
            content="Mock EM roadmap plan",
            name="engineering_manager"
        )
        mock_em_llm.return_value = em_instance
        
        # Mock RA response
        ra_instance = MagicMock()
        ra_instance.invoke.return_value = AIMessage(
            content="# Project Overview\n\nMock requirements specification document.",
            name="requirement_analyst"
        )
        mock_ra_llm.return_value = ra_instance
        
        yield {
            "em": em_instance,
            "ra": ra_instance
        }

def test_requirement_analyst_initialization():
    """Test that RequirementAnalystAgent initializes and loads prompts correctly."""
    agent = RequirementAnalystAgent()
    assert agent.system_prompt != ""
    assert "Senior Requirement Analyst" in agent.system_prompt

def test_requirement_analyst_run(temp_artifact_dir, mock_llm_responses):
    """Test RequirementAnalystAgent run method, state updates, and artifact creation."""
    agent = RequirementAnalystAgent()
    # Override artifact manager's root_dir to use the temp directory
    agent.artifact_manager = ArtifactManager(root_dir=temp_artifact_dir)
    
    state: ForgeState = {
        "user_request": "Build a library management system",
        "current_stage": WorkflowStages.ENGINEERING_MANAGEMENT,
        "approval_status": ApprovalStatuses.PENDING,
        "requirements": None,
        "architecture": None,
        "backend_blueprint": None,
        "implementation": None,
        "qa_report": None,
        "security_report": None,
        "review_report": None,
        "deployment_blueprint": None,
        "artifacts": {},
        "messages": [
            AIMessage(content="Mock EM planning response", name="engineering_manager")
        ],
        "metadata": {}
    }
    
    # Run agent
    updates = agent.run(state)
    
    # Check returned state updates
    assert updates["current_stage"] == WorkflowStages.REQUIREMENT_ANALYSIS
    assert updates["requirements"] == "# Project Overview\n\nMock requirements specification document."
    assert "requirements" in updates["artifacts"]
    
    saved_path = updates["artifacts"]["requirements"][0]
    assert os.path.exists(saved_path)
    assert "requirements_v1.md" in saved_path
    
    with open(saved_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Mock requirements specification document." in content

def test_version_increment_non_overwriting(temp_artifact_dir, mock_llm_responses):
    """Verify that multiple executions increment artifact version and do not overwrite."""
    agent = RequirementAnalystAgent()
    agent.artifact_manager = ArtifactManager(root_dir=temp_artifact_dir)
    
    state: ForgeState = {
        "user_request": "Build a library management system",
        "current_stage": WorkflowStages.ENGINEERING_MANAGEMENT,
        "approval_status": ApprovalStatuses.PENDING,
        "requirements": None,
        "architecture": None,
        "backend_blueprint": None,
        "implementation": None,
        "qa_report": None,
        "security_report": None,
        "review_report": None,
        "deployment_blueprint": None,
        "artifacts": {},
        "messages": [
            AIMessage(content="Mock EM planning response", name="engineering_manager")
        ],
        "metadata": {}
    }
    
    # Execute first time
    updates_1 = agent.run(state)
    path_1 = updates_1["artifacts"]["requirements"][0]
    assert "requirements_v1.md" in path_1
    
    # Execute second time (simulate subsequent run/retry)
    updates_2 = agent.run(state)
    path_2 = updates_2["artifacts"]["requirements"][0]
    assert "requirements_v2.md" in path_2
    
    # Check both files exist
    assert os.path.exists(path_1)
    assert os.path.exists(path_2)
    assert path_1 != path_2

def test_workflow_execution_integration(temp_artifact_dir, mock_llm_responses):
    """Verify end-to-end workflow execution routes EM -> RA -> END and stores artifacts."""
    # We want to test the compiled graph's routing.
    # We patch settings.ARTIFACT_ROOT to write to temp_artifact_dir.
    with patch("app.settings.settings.ARTIFACT_ROOT", new=temp_artifact_dir):
        
        workflow = ForgeWorkflow()
        final_state = workflow.execute("Build a simple FastAPI todo API")
        
        # Verify transitions and final state
        assert final_state["current_stage"] == WorkflowStages.REQUIREMENT_ANALYSIS
        assert final_state["approval_status"] == ApprovalStatuses.PENDING
        assert len(final_state["messages"]) == 2
        
        # First message from EM, second from RA
        assert final_state["messages"][0].name == "engineering_manager"
        assert final_state["messages"][1].name == "requirement_analyst"
        
        # Verify artifact list
        assert "requirements" in final_state["artifacts"]
        saved_path = final_state["artifacts"]["requirements"][0]
        assert os.path.exists(saved_path)
        assert "requirements_v1.md" in saved_path
        assert final_state["requirements"] is not None
        assert "Mock requirements specification document." in final_state["requirements"]
        
        # Verify metadata
        assert final_state["metadata"].get("engineering_manager_analysis_completed") is True
        assert final_state["metadata"].get("requirement_analysis_completed") is True
