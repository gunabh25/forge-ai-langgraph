"""Unit and integration tests for the SolutionArchitectAgent and workflow integration."""

import os
from typing import Dict, Any
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from agents.solution_architect.agent import SolutionArchitectAgent
from app.state import ForgeState
from app.workflow import ForgeWorkflow
from core.constants import WorkflowStages, ApprovalStatuses
from core.artifact_manager import ArtifactManager
from core.approval import ApprovalInterface, ApprovalResult

@pytest.fixture
def temp_artifact_dir(tmp_path):
    """Fixture to provide a clean temporary directory for artifact testing."""
    return str(tmp_path)

@pytest.fixture
def mock_llm_responses():
    """Mock the LLMs for EM, RA, SA, BE, and ASE agents."""
    import json
    ase_workspace = json.dumps({
        "src/main.py": "# main\n",
        "Dockerfile": "FROM python:3.12-slim\n",
        "README.md": "# App\n",
    })

    with patch("agents.engineering_manager.agent.get_llm") as mock_em_llm, \
         patch("agents.requirement_analyst.agent.get_llm") as mock_ra_llm, \
         patch("agents.solution_architect.agent.get_llm") as mock_sa_llm, \
         patch("agents.backend_engineer.agent.get_llm") as mock_be_llm, \
         patch("agents.ai_software_engineer.agent.get_llm") as mock_ase_llm:
         
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
            content="# Project Overview\n\nMock requirements specification.",
            name="requirement_analyst"
        )
        mock_ra_llm.return_value = ra_instance
        
        # Mock SA response
        sa_instance = MagicMock()
        sa_instance.invoke.return_value = AIMessage(
            content="# Executive Summary\n\nMock architecture specification.",
            name="solution_architect"
        )
        mock_sa_llm.return_value = sa_instance
        
        # Mock BE response
        be_instance = MagicMock()
        be_instance.invoke.return_value = AIMessage(
            content="# Executive Summary\n\nMock backend blueprint.",
            name="backend_engineer"
        )
        mock_be_llm.return_value = be_instance

        # Mock ASE response
        ase_instance = MagicMock()
        ase_instance.invoke.return_value = AIMessage(
            content=ase_workspace,
            name="ai_software_engineer"
        )
        mock_ase_llm.return_value = ase_instance
        
        yield {
            "em": em_instance,
            "ra": ra_instance,
            "sa": sa_instance,
            "be": be_instance,
            "ase": ase_instance,
        }

def test_solution_architect_initialization():
    """Test that SolutionArchitectAgent initializes and loads prompts correctly."""
    agent = SolutionArchitectAgent()
    assert agent.system_prompt != ""
    assert "Principal Software Architect" in agent.system_prompt

def test_solution_architect_run(temp_artifact_dir, mock_llm_responses):
    """Test SolutionArchitectAgent run method, state updates, and artifact creation."""
    agent = SolutionArchitectAgent()
    agent.artifact_manager = ArtifactManager(root_dir=temp_artifact_dir)
    
    # pyrefly: ignore [bad-typed-dict-key]
    state: ForgeState = {
        "user_request": "Build a library management system",
        "current_stage": WorkflowStages.REQUIREMENT_ANALYSIS,
        "approval_status": ApprovalStatuses.PENDING,
        "requirements": "# Project Overview\n\nMock requirements specification.",
        "architecture": None,
        "backend_blueprint": None,
        "implementation": None,
        "qa_report": None,
        "security_report": None,
        "review_report": None,
        "deployment_blueprint": None,
        "artifacts": {
            "requirements": ["/path/to/requirements_v1.md"]
        },
        "messages": [
            AIMessage(content="Mock EM planning response", name="engineering_manager"),
            AIMessage(content="# Project Overview\n\nMock requirements specification.", name="requirement_analyst")
        ],
        "metadata": {}
    }
    
    # Run agent
    updates = agent.run(state)
    
    # Check returned state updates
    assert updates["current_stage"] == WorkflowStages.SOLUTION_ARCHITECTURE
    assert updates["architecture"] == "# Executive Summary\n\nMock architecture specification."
    assert "architecture" in updates["artifacts"]
    
    saved_path = updates["artifacts"]["architecture"][0]
    assert os.path.exists(saved_path)
    assert "architecture_v1.md" in saved_path
    
    with open(saved_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Mock architecture specification." in content

def test_version_increment_non_overwriting(temp_artifact_dir, mock_llm_responses):
    """Verify that multiple executions increment architecture artifact version sequentially."""
    agent = SolutionArchitectAgent()
    agent.artifact_manager = ArtifactManager(root_dir=temp_artifact_dir)
    
    # pyrefly: ignore [bad-typed-dict-key]
    state: ForgeState = {
        "user_request": "Build a library management system",
        "current_stage": WorkflowStages.REQUIREMENT_ANALYSIS,
        "approval_status": ApprovalStatuses.PENDING,
        "requirements": "# Project Overview\n\nMock requirements specification.",
        "architecture": None,
        "backend_blueprint": None,
        "implementation": None,
        "qa_report": None,
        "security_report": None,
        "review_report": None,
        "deployment_blueprint": None,
        "artifacts": {
            "requirements": ["/path/to/requirements_v1.md"]
        },
        "messages": [
            AIMessage(content="Mock EM planning response", name="engineering_manager"),
            AIMessage(content="# Project Overview\n\nMock requirements specification.", name="requirement_analyst")
        ],
        "metadata": {}
    }
    
    # Execute first time
    updates_1 = agent.run(state)
    path_1 = updates_1["artifacts"]["architecture"][0]
    assert "architecture_v1.md" in path_1
    
    # Execute second time (simulate subsequent run/retry)
    updates_2 = agent.run(state)
    path_2 = updates_2["artifacts"]["architecture"][0]
    assert "architecture_v2.md" in path_2
    
    # Check both files exist
    assert os.path.exists(path_1)
    assert os.path.exists(path_2)
    assert path_1 != path_2

class MockApproval(ApprovalInterface):
    def request_approval(self, stage: str, context: Dict[str, Any]) -> ApprovalResult:
        return ApprovalResult(status=ApprovalStatuses.APPROVED)

def test_workflow_execution_integration(temp_artifact_dir, mock_llm_responses):
    """Verify end-to-end workflow execution routes EM -> RA -> SA -> HUMAN_APPROVAL -> BE -> ASE -> END."""
    with patch("app.settings.settings.ARTIFACT_ROOT", new=temp_artifact_dir):
        
        workflow = ForgeWorkflow(approval_interface=MockApproval())
        final_state = workflow.execute("Build a simple FastAPI todo API")
        
        # Verify transitions and final state
        assert final_state["current_stage"] == WorkflowStages.AI_SOFTWARE_ENGINEERING
        assert final_state["approval_status"] == ApprovalStatuses.APPROVED
        assert len(final_state["messages"]) == 5
        
        # Messages from EM, RA, SA, BE, and ASE
        assert final_state["messages"][0].name == "engineering_manager"
        assert final_state["messages"][1].name == "requirement_analyst"
        assert final_state["messages"][2].name == "solution_architect"
        assert final_state["messages"][3].name == "backend_engineer"
        assert final_state["messages"][4].name == "ai_software_engineer"
        
        # Verify artifact list
        assert "requirements" in final_state["artifacts"]
        assert "architecture" in final_state["artifacts"]
        assert "backend" in final_state["artifacts"]
        assert "implementation" in final_state["artifacts"]
        
        saved_reqs_path = final_state["artifacts"]["requirements"][0]
        saved_arch_path = final_state["artifacts"]["architecture"][0]
        saved_back_path = final_state["artifacts"]["backend"][0]
        
        assert os.path.exists(saved_reqs_path)
        assert os.path.exists(saved_arch_path)
        assert os.path.exists(saved_back_path)
        assert "requirements_v1.md" in saved_reqs_path
        assert "architecture_v1.md" in saved_arch_path
        assert "backend_blueprint_v1.md" in saved_back_path
        
        assert final_state["requirements"] is not None
        assert final_state["architecture"] is not None
        assert final_state["backend_blueprint"] is not None
        
        # Verify metadata
        assert final_state["metadata"].get("engineering_manager_analysis_completed") is True
        assert final_state["metadata"].get("requirement_analysis_completed") is True
        assert final_state["metadata"].get("solution_architecture_completed") is True
        assert final_state["metadata"].get("backend_engineering_completed") is True
        assert final_state["metadata"].get("ai_software_engineering_completed") is True
