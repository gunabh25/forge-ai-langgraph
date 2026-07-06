"""Unit and integration tests for the BackendEngineerAgent and approval gating."""

import os
from typing import Dict, Any
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from agents.backend_engineer.agent import BackendEngineerAgent
from app.state import ForgeState
from app.workflow import ForgeWorkflow
from core.constants import WorkflowStages, ApprovalStatuses
from core.artifact_manager import ArtifactManager
from core.approval import ApprovalInterface, ApprovalResult

@pytest.fixture
def temp_artifact_dir(tmp_path):
    """Fixture to provide a clean temporary directory for artifact testing."""
    return str(tmp_path)

class SimulatedApprovalInterface(ApprovalInterface):
    """Test approval interface to simulate choices without blocking."""
    
    def __init__(self, decision: str, feedback: str = ""):
        self.decision = decision
        self.feedback = feedback
        
    def request_approval(self, stage: str, context: Dict[str, Any]) -> ApprovalResult:
        return ApprovalResult(status=self.decision, feedback=self.feedback)

@pytest.fixture
def mock_all_agent_llms():
    """Mock LLMs for EM, RA, SA, BE, and ASE agents."""
    import json
    ase_workspace = json.dumps({
        "src/main.py": "# main\n",
        "Dockerfile": "FROM python:3.12-slim\n",
        "README.md": "# App\n",
    })

    with patch("agents.engineering_manager.agent.get_llm") as mock_em, \
         patch("agents.requirement_analyst.agent.get_llm") as mock_ra, \
         patch("agents.solution_architect.agent.get_llm") as mock_sa, \
         patch("agents.backend_engineer.agent.get_llm") as mock_be, \
         patch("agents.ai_software_engineer.agent.get_llm") as mock_ase:
         
        # EM
        em_inst = MagicMock()
        em_inst.invoke.return_value = AIMessage(content="EM plan", name="engineering_manager")
        mock_em.return_value = em_inst
        
        # RA
        ra_inst = MagicMock()
        ra_inst.invoke.return_value = AIMessage(content="# Project Overview\n\nRequirements docs.", name="requirement_analyst")
        mock_ra.return_value = ra_inst
        
        # SA
        sa_inst = MagicMock()
        sa_inst.invoke.return_value = AIMessage(
            content="# Executive Summary\n\n# Architecture Pattern\nModular Monolith\n\n# Technology Stack\n- **Database**: PostgreSQL\n- **Authentication**: JWT\n\n# API Design\nGET /api/v1/sales\n\n# Scalability Strategy\nHorizontal scaling",
            name="solution_architect"
        )
        mock_sa.return_value = sa_inst
        
        # BE
        be_inst = MagicMock()
        be_inst.invoke.return_value = AIMessage(content="# Executive Summary\n\nBackend blueprint docs.", name="backend_engineer")
        mock_be.return_value = be_inst

        # ASE
        ase_inst = MagicMock()
        ase_inst.invoke.return_value = AIMessage(content=ase_workspace, name="ai_software_engineer")
        mock_ase.return_value = ase_inst
        
        yield {
            "em": em_inst,
            "ra": ra_inst,
            "sa": sa_inst,
            "be": be_inst,
            "ase": ase_inst,
        }

def test_backend_engineer_initialization():
    """Test that BackendEngineerAgent initializes and loads prompts correctly."""
    agent = BackendEngineerAgent()
    assert agent.system_prompt != ""
    assert "Principal Backend Engineer" in agent.system_prompt

def test_backend_engineer_run(temp_artifact_dir, mock_all_agent_llms):
    """Test BackendEngineerAgent run method, state updates, and artifact creation."""
    agent = BackendEngineerAgent()
    agent.artifact_manager = ArtifactManager(root_dir=temp_artifact_dir)
    
    # pyrefly: ignore [bad-typed-dict-key]
    state: ForgeState = {
        "user_request": "Build a library management system",
        "current_stage": WorkflowStages.HUMAN_APPROVAL,
        "approval_status": ApprovalStatuses.APPROVED,
        "approval_history": [],
        "requirements": "# Project Overview\n\nRequirements docs.",
        "architecture": "# Executive Summary\n\nArchitecture docs.",
        "backend_blueprint": None,
        "implementation": None,
        "qa_report": None,
        "security_report": None,
        "review_report": None,
        "deployment_blueprint": None,
        "artifacts": {
            "requirements": ["/path/to/requirements_v1.md"],
            "architecture": ["/path/to/architecture_v1.md"]
        },
        "messages": [
            AIMessage(content="EM plan", name="engineering_manager"),
            AIMessage(content="Requirements docs.", name="requirement_analyst"),
            AIMessage(content="Architecture docs.", name="solution_architect")
        ],
        "metadata": {}
    }
    
    # Run agent
    updates = agent.run(state)
    
    # Check returned state updates
    assert updates["current_stage"] == WorkflowStages.BACKEND_ENGINEERING
    assert updates["backend_blueprint"] == "# Executive Summary\n\nBackend blueprint docs."
    assert "backend" in updates["artifacts"]
    
    saved_path = updates["artifacts"]["backend"][0]
    assert os.path.exists(saved_path)
    assert "backend_blueprint_v1.md" in saved_path
    
    with open(saved_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Backend blueprint docs." in content

def test_backend_version_increment_non_overwriting(temp_artifact_dir, mock_all_agent_llms):
    """Verify that multiple executions increment backend blueprint version sequentially."""
    agent = BackendEngineerAgent()
    agent.artifact_manager = ArtifactManager(root_dir=temp_artifact_dir)
    
    # pyrefly: ignore [bad-typed-dict-key]
    state: ForgeState = {
        "user_request": "Build a library management system",
        "current_stage": WorkflowStages.HUMAN_APPROVAL,
        "approval_status": ApprovalStatuses.APPROVED,
        "approval_history": [],
        "requirements": "# Project Overview\n\nRequirements docs.",
        "architecture": "# Executive Summary\n\nArchitecture docs.",
        "backend_blueprint": None,
        "implementation": None,
        "qa_report": None,
        "security_report": None,
        "review_report": None,
        "deployment_blueprint": None,
        "artifacts": {
            "requirements": ["/path/to/requirements_v1.md"],
            "architecture": ["/path/to/architecture_v1.md"]
        },
        "messages": [
            AIMessage(content="EM plan", name="engineering_manager"),
            AIMessage(content="Requirements docs.", name="requirement_analyst"),
            AIMessage(content="Architecture docs.", name="solution_architect")
        ],
        "metadata": {}
    }
    
    # Execute first time
    updates_1 = agent.run(state)
    path_1 = updates_1["artifacts"]["backend"][0]
    assert "backend_blueprint_v1.md" in path_1
    
    # Execute second time (simulate subsequent run/retry)
    updates_2 = agent.run(state)
    path_2 = updates_2["artifacts"]["backend"][0]
    assert "backend_blueprint_v2.md" in path_2
    
    # Check both files exist
    assert os.path.exists(path_1)
    assert os.path.exists(path_2)
    assert path_1 != path_2

def test_workflow_execution_approved(temp_artifact_dir, mock_all_agent_llms):
    """Verify end-to-end workflow execution when human APPROVES the architecture."""
    with patch("app.settings.settings.ARTIFACT_ROOT", new=temp_artifact_dir):
        
        # Inject the auto-approver interface
        workflow = ForgeWorkflow(approval_interface=SimulatedApprovalInterface(ApprovalStatuses.APPROVED))
        final_state = workflow.execute("Build a simple FastAPI todo API")
        
        # Verify transitions and final state
        assert final_state["current_stage"] == WorkflowStages.FINAL_REPORT_GENERATION
        assert final_state["approval_status"] == ApprovalStatuses.APPROVED
        assert len(final_state["messages"]) == 5
        
        # Check messages list
        assert final_state["messages"][0].name == "engineering_manager"
        assert final_state["messages"][1].name == "requirement_analyst"
        assert final_state["messages"][2].name == "solution_architect"
        assert final_state["messages"][3].name == "backend_engineer"
        assert final_state["messages"][4].name == "ai_software_engineer"
        
        # Verify history logs
        assert len(final_state["approval_history"]) == 1
        assert final_state["approval_history"][0]["decision"] == ApprovalStatuses.APPROVED
        assert final_state["approval_history"][0]["stage"] == WorkflowStages.SOLUTION_ARCHITECTURE
        
        # Verify artifacts
        assert "requirements" in final_state["artifacts"]
        assert "architecture" in final_state["artifacts"]
        assert "backend" in final_state["artifacts"]

def test_workflow_execution_rejected(temp_artifact_dir, mock_all_agent_llms):
    """Verify end-to-end workflow termination when human REJECTS the architecture."""
    with patch("app.settings.settings.ARTIFACT_ROOT", new=temp_artifact_dir):
        
        # Inject the auto-rejecter interface
        workflow = ForgeWorkflow(approval_interface=SimulatedApprovalInterface(ApprovalStatuses.REJECTED, "Not good enough"))
        final_state = workflow.execute("Build a simple FastAPI todo API")
        
        # Verify transitions and final state
        assert final_state["current_stage"] == WorkflowStages.HUMAN_APPROVAL
        assert final_state["approval_status"] == ApprovalStatuses.REJECTED
        assert len(final_state["messages"]) == 3  # EM, RA, SA (no BE message!)
        
        assert len(final_state["approval_history"]) == 1
        assert final_state["approval_history"][0]["decision"] == ApprovalStatuses.REJECTED
        assert final_state["approval_history"][0]["feedback"] == "Not good enough"
        
        # Verify no backend blueprint artifact was created
        assert "backend" not in final_state["artifacts"]

def test_workflow_execution_changes_requested(temp_artifact_dir, mock_all_agent_llms):
    """Verify end-to-end loopback when human REQUESTS CHANGES and then APPROVES."""
    with patch("app.settings.settings.ARTIFACT_ROOT", new=temp_artifact_dir):
        
        # We need a stateful mock approval interface that returns Changes Requested first, then Approved
        class DynamicApproval(ApprovalInterface):
            def __init__(self):
                self.calls = 0
            def request_approval(self, stage: str, context: Dict[str, Any]) -> ApprovalResult:
                self.calls += 1
                if self.calls == 1:
                    return ApprovalResult(status=ApprovalStatuses.CHANGES_REQUESTED, feedback="Add Redis caching.")
                return ApprovalResult(status=ApprovalStatuses.APPROVED)
                
        workflow = ForgeWorkflow(approval_interface=DynamicApproval())
        final_state = workflow.execute("Build a simple FastAPI todo API")
        
        # Verify transitions and final state
        assert final_state["current_stage"] == WorkflowStages.FINAL_REPORT_GENERATION
        assert final_state["approval_status"] == ApprovalStatuses.APPROVED
        
        # Verify approval history logs both decisions
        assert len(final_state["approval_history"]) == 2
        assert final_state["approval_history"][0]["decision"] == ApprovalStatuses.CHANGES_REQUESTED
        assert final_state["approval_history"][0]["feedback"] == "Add Redis caching."
        assert final_state["approval_history"][1]["decision"] == ApprovalStatuses.APPROVED
        
        # Check messages: EM, RA, SA (first try), SA (revised try), BE, ASE
        assert len(final_state["messages"]) == 6
        assert final_state["messages"][0].name == "engineering_manager"
        assert final_state["messages"][1].name == "requirement_analyst"
        assert final_state["messages"][2].name == "solution_architect"
        assert final_state["messages"][3].name == "solution_architect"
        assert final_state["messages"][4].name == "backend_engineer"
        assert final_state["messages"][5].name == "ai_software_engineer"
        
        # Verify that both versions of architecture were saved
        assert len(final_state["artifacts"]["architecture"]) == 2
        assert "architecture_v1.md" in final_state["artifacts"]["architecture"][0]
        assert "architecture_v2.md" in final_state["artifacts"]["architecture"][1]
