"""Unit tests for the ForgeAI LangGraph workflow and Engineering Manager."""

from typing import cast
from unittest.mock import MagicMock, patch
import pytest
from langchain_core.messages import AIMessage
from agents.engineering_manager.agent import EngineeringManagerAgent
from app.state import validate_forge_state, ForgeState
from app.router import WorkflowRouter
from app.graph import compile_workflow
from app.workflow import ForgeWorkflow
from core.constants import WorkflowStages, ApprovalStatuses

@pytest.fixture
def mock_llm_invoke():
    """Mock the LLM's invoke method to return a dummy response."""
    with patch("agents.engineering_manager.agent.get_llm") as mock_get_llm_em, \
         patch("agents.requirement_analyst.agent.get_llm") as mock_get_llm_ra:
         
        mock_llm_em = MagicMock()
        mock_llm_em.invoke.return_value = AIMessage(content="Mock EM planning response", name="engineering_manager")
        mock_get_llm_em.return_value = mock_llm_em
        
        mock_llm_ra = MagicMock()
        mock_llm_ra.invoke.return_value = AIMessage(content="# Project Overview\n\nMock requirements specification document.", name="requirement_analyst")
        mock_get_llm_ra.return_value = mock_llm_ra
        
        yield (mock_llm_em, mock_llm_ra)

def test_state_validation_valid_before():
    """Test state validation before execution succeeds with valid input."""
    state = {
        "user_request": "Build a chatbot",
        "current_stage": "",
        "approval_status": "pending",
        "requirements": None,
        "architecture": None,
        "backend_blueprint": None,
        "implementation": None,
        "qa_report": None,
        "security_report": None,
        "review_report": None,
        "deployment_blueprint": None,
        "artifacts": {},
        "messages": [],
        "metadata": {}
    }
    # Should not raise any exception
    validate_forge_state(state, is_before_execution=True)

def test_state_validation_invalid_before():
    """Test state validation before execution raises ValueError for invalid input."""
    # Missing user_request
    state_missing = {
        "current_stage": ""
    }
    with pytest.raises(ValueError, match="user_request"):
        validate_forge_state(state_missing, is_before_execution=True)

    # Empty user_request
    state_empty = {
        "user_request": "   ",
        "current_stage": ""
    }
    with pytest.raises(ValueError, match="user_request"):
        validate_forge_state(state_empty, is_before_execution=True)

def test_state_validation_invalid_after():
    """Test state validation after execution raises ValueError if key results are missing."""
    # Missing current_stage
    state_no_stage = {
        "user_request": "Build a chatbot",
        "current_stage": "",
        "approval_status": "pending",
        "messages": [AIMessage(content="hello")],
        "metadata": {}
    }
    with pytest.raises(ValueError, match="current_stage"):
        validate_forge_state(state_no_stage, is_before_execution=False)

    # Missing messages
    state_no_messages = {
        "user_request": "Build a chatbot",
        "current_stage": "engineering_management",
        "approval_status": "pending",
        "messages": [],
        "metadata": {}
    }
    with pytest.raises(ValueError, match="messages"):
        validate_forge_state(state_no_messages, is_before_execution=False)

def test_router_transitions():
    """Test router resolves next steps correctly."""
    # Test initial routing (if current_stage is empty)
    state_initial = cast(
        ForgeState,
        {
            "user_request": "Build a chatbot",
            "current_stage": "",
            "approval_status": "pending",
            "messages": [],
            "metadata": {}
        }
    )
    next_stage = WorkflowRouter.get_next_stage(state_initial)
    assert next_stage == WorkflowStages.ENGINEERING_MANAGEMENT

    # Test routing from Engineering Management (should route to REQUIREMENT_ANALYSIS)
    state_em = cast(
        ForgeState,
        {
            "user_request": "Build a chatbot",
            "current_stage": WorkflowStages.ENGINEERING_MANAGEMENT,
            "approval_status": "pending",
            "messages": [],
            "metadata": {}
        }
    )
    next_stage = WorkflowRouter.get_next_stage(state_em)
    assert next_stage == WorkflowStages.REQUIREMENT_ANALYSIS

    # Test routing from Requirement Analysis (should end for Milestone 4)
    state_ra = cast(
        ForgeState,
        {
            "user_request": "Build a chatbot",
            "current_stage": WorkflowStages.REQUIREMENT_ANALYSIS,
            "approval_status": "pending",
            "messages": [],
            "metadata": {}
        }
    )
    next_stage_ra = WorkflowRouter.get_next_stage(state_ra)
    assert next_stage_ra == "END"

def test_graph_compilation(mock_llm_invoke):
    """Verify that the StateGraph compiles successfully."""
    compiled_app = compile_workflow()
    assert compiled_app is not None

def test_workflow_execution(mock_llm_invoke):
    """Verify workflow initialization, execution, and output state."""
    workflow = ForgeWorkflow()
    final_state = workflow.execute("Build a simple FastAPI todo API")

    # Verify key state values are updated
    assert final_state["current_stage"] == WorkflowStages.REQUIREMENT_ANALYSIS
    assert final_state["approval_status"] == ApprovalStatuses.PENDING
    assert len(final_state["messages"]) == 2
    assert final_state["messages"][0].content == "Mock EM planning response"
    assert final_state["messages"][1].content == "# Project Overview\n\nMock requirements specification document."
    assert final_state["metadata"]["engineering_manager_analysis_completed"] is True
    assert final_state["metadata"]["requirement_analysis_completed"] is True
