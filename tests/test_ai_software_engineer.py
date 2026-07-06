"""Tests for AISoftwareEngineerAgent, WorkspaceParser, and end-to-end workflow."""

import json
import os
from typing import Dict, Any

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage

from agents.ai_software_engineer.agent import AISoftwareEngineerAgent, WorkspaceParser
from app.state import ForgeState
from app.workflow import ForgeWorkflow
from core.artifact_manager import ArtifactManager
from core.approval import ApprovalInterface, ApprovalResult
from core.constants import WorkflowStages, ApprovalStatuses

# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

MINIMAL_WORKSPACE = {
    "src/main.py": "# main entry point\nprint('hello')\n",
    "src/controllers/user_controller.py": "# user controller\n",
    "src/services/user_service.py": "# user service\n",
    "src/models/user.py": "# user model\n",
    "Dockerfile": "FROM python:3.12-slim\nCMD [\"python\", \"src/main.py\"]\n",
    "README.md": "# My Project\n",
    "requirements.txt": "fastapi==0.111.0\n",
}

MINIMAL_WORKSPACE_JSON = json.dumps(MINIMAL_WORKSPACE, indent=2)


@pytest.fixture
def temp_artifact_dir(tmp_path):
    """Provide a clean temporary directory for artifact testing."""
    return str(tmp_path)


@pytest.fixture
def sample_state() -> ForgeState:
    """Minimal valid ForgeState for ASE testing."""
    return {  # type: ignore[return-value]
        "user_request": "Build a REST API for a bookstore",
        "current_stage": WorkflowStages.BACKEND_ENGINEERING,
        "approval_status": ApprovalStatuses.APPROVED,
        "approval_history": [],
        "requirements": "# Requirements\n\nBuild a bookstore REST API with CRUD for books and authors.",
        "architecture": "# Architecture\n\nFastAPI + PostgreSQL + JWT auth.",
        "backend_blueprint": "# Backend Blueprint\n\nControllers: BookController, AuthorController.\nServices: BookService, AuthorService.",
        "implementation": None,
        "qa_report": None,
        "security_report": None,
        "review_report": None,
        "deployment_blueprint": None,
        "generated_files": {},
        "artifacts": {
            "requirements": ["/tmp/requirements_v1.md"],
            "architecture": ["/tmp/architecture_v1.md"],
            "backend": ["/tmp/backend_blueprint_v1.md"],
        },
        "messages": [
            AIMessage(content="EM plan", name="engineering_manager"),
            AIMessage(content="Requirements.", name="requirement_analyst"),
            AIMessage(content="Architecture.", name="solution_architect"),
            AIMessage(content="Blueprint.", name="backend_engineer"),
        ],
        "metadata": {},
    }


@pytest.fixture
def mock_ase_llm():
    """Mock LLM that returns a valid workspace JSON response."""
    inst = MagicMock()
    inst.invoke.return_value = AIMessage(
        content=MINIMAL_WORKSPACE_JSON,
        name="ai_software_engineer",
    )
    return inst


class SimulatedApproval(ApprovalInterface):
    """Non-blocking approval interface for integration tests."""

    def __init__(self, decision: str = ApprovalStatuses.APPROVED, feedback: str = ""):
        self.decision = decision
        self.feedback = feedback

    def request_approval(self, stage: str, context: Dict[str, Any]) -> ApprovalResult:
        return ApprovalResult(status=self.decision, feedback=self.feedback)


# ---------------------------------------------------------------------------
# WorkspaceParser tests
# ---------------------------------------------------------------------------


def test_workspace_parser_plain_json():
    """Parses a plain JSON object successfully."""
    workspace = WorkspaceParser.extract(MINIMAL_WORKSPACE_JSON)
    assert set(workspace.keys()) == set(MINIMAL_WORKSPACE.keys())
    assert workspace["README.md"] == MINIMAL_WORKSPACE["README.md"]


def test_workspace_parser_markdown_fenced_json():
    """Strips a markdown ```json code fence before parsing."""
    fenced = f"```json\n{MINIMAL_WORKSPACE_JSON}\n```"
    workspace = WorkspaceParser.extract(fenced)
    assert "src/main.py" in workspace


def test_workspace_parser_generic_fence():
    """Strips a plain ``` code fence (no language tag) before parsing."""
    fenced = f"```\n{MINIMAL_WORKSPACE_JSON}\n```"
    workspace = WorkspaceParser.extract(fenced)
    assert "Dockerfile" in workspace


def test_workspace_parser_prose_prefix():
    """Handles responses that have prose before the JSON object."""
    response = "Here is the generated workspace:\n\n" + MINIMAL_WORKSPACE_JSON
    workspace = WorkspaceParser.extract(response)
    assert "src/main.py" in workspace


def test_workspace_parser_invalid_json_raises():
    """Raises ValueError when response contains braces but is not valid JSON."""
    with pytest.raises(ValueError, match="Failed to parse LLM response as JSON"):
        WorkspaceParser.extract("{ not valid json at all }")


def test_workspace_parser_no_json_object_raises():
    """Raises ValueError when there is no JSON object in the response."""
    with pytest.raises(ValueError, match="does not contain a JSON object"):
        WorkspaceParser.extract("  no braces here  ")


def test_workspace_parser_non_string_value_raises():
    """Raises ValueError when a file value is not a string."""
    bad_workspace = {"src/main.py": 42, "README.md": "# Readme\n"}
    with pytest.raises(ValueError, match="non-string values"):
        WorkspaceParser.extract(json.dumps(bad_workspace))


def test_workspace_parser_empty_object_raises():
    """Raises ValueError when the workspace JSON is an empty object."""
    with pytest.raises(ValueError, match="empty workspace"):
        WorkspaceParser.extract("{}")


# ---------------------------------------------------------------------------
# AISoftwareEngineerAgent unit tests
# ---------------------------------------------------------------------------


def test_ase_initialization():
    """Agent initialises and loads the system prompt correctly."""
    agent = AISoftwareEngineerAgent()
    assert agent.system_prompt != ""
    assert "Principal Software Engineer" in agent.system_prompt


def test_ase_run_updates_state(temp_artifact_dir, sample_state, mock_ase_llm):
    """Agent.run returns correct state slice with generated_files and artifacts."""
    agent = AISoftwareEngineerAgent(llm=mock_ase_llm)
    agent.artifact_manager = ArtifactManager(root_dir=temp_artifact_dir)

    updates = agent.run(sample_state)

    # Stage updated
    assert updates["current_stage"] == WorkflowStages.AI_SOFTWARE_ENGINEERING

    # generated_files populated
    assert isinstance(updates["generated_files"], dict)
    assert "src/main.py" in updates["generated_files"]
    assert "Dockerfile" in updates["generated_files"]
    assert len(updates["generated_files"]) == len(MINIMAL_WORKSPACE)

    # implementation summary exists
    assert "Generated" in updates["implementation"]

    # Message appended
    assert len(updates["messages"]) == 1
    assert updates["messages"][0].name == "ai_software_engineer"

    # Metadata updated
    assert updates["metadata"]["ai_software_engineering_completed"] is True
    assert updates["metadata"]["generated_file_count"] == len(MINIMAL_WORKSPACE)


def test_ase_run_writes_files_to_disk(temp_artifact_dir, sample_state, mock_ase_llm):
    """Agent.run writes every generated file to the artifact directory."""
    agent = AISoftwareEngineerAgent(llm=mock_ase_llm)
    agent.artifact_manager = ArtifactManager(root_dir=temp_artifact_dir)

    updates = agent.run(sample_state)

    generated_base = os.path.join(
        temp_artifact_dir, "implementation", "generated"
    )
    assert os.path.isdir(generated_base)

    for rel_path in MINIMAL_WORKSPACE.keys():
        abs_path = os.path.join(generated_base, rel_path)
        assert os.path.exists(abs_path), f"Expected file not found: {rel_path}"
        with open(abs_path, encoding="utf-8") as f:
            assert f.read() == MINIMAL_WORKSPACE[rel_path]


def test_ase_run_registers_manifest_artifact(temp_artifact_dir, sample_state, mock_ase_llm):
    """Agent registers an implementation manifest in artifacts."""
    agent = AISoftwareEngineerAgent(llm=mock_ase_llm)
    agent.artifact_manager = ArtifactManager(root_dir=temp_artifact_dir)

    updates = agent.run(sample_state)

    assert "implementation" in updates["artifacts"]
    paths = updates["artifacts"]["implementation"]
    # First entry is the manifest file
    manifest_path = paths[0]
    assert os.path.exists(manifest_path)
    assert "implementation_manifest_v1.md" in manifest_path
    content = open(manifest_path, encoding="utf-8").read()
    assert "Implementation Manifest" in content
    assert "src/main.py" in content


def test_ase_manifest_versioning(temp_artifact_dir, sample_state, mock_ase_llm):
    """Running agent twice increments manifest version (non-overwriting)."""
    agent = AISoftwareEngineerAgent(llm=mock_ase_llm)
    agent.artifact_manager = ArtifactManager(root_dir=temp_artifact_dir)

    updates_1 = agent.run(sample_state)
    updates_2 = agent.run(sample_state)

    path_1 = updates_1["artifacts"]["implementation"][0]
    path_2 = updates_2["artifacts"]["implementation"][0]

    assert "v1" in path_1
    assert "v2" in path_2
    assert path_1 != path_2
    assert os.path.exists(path_1)
    assert os.path.exists(path_2)


def test_ase_raises_when_backend_blueprint_missing(sample_state):
    """Agent raises ValueError when backend_blueprint is missing."""
    sample_state["backend_blueprint"] = None  # type: ignore[typeddict-item]
    agent = AISoftwareEngineerAgent(llm=MagicMock())
    with pytest.raises(ValueError, match="backend_blueprint"):
        agent.run(sample_state)


def test_ase_raises_when_requirements_missing(sample_state):
    """Agent raises ValueError when requirements are missing."""
    sample_state["requirements"] = ""  # type: ignore[typeddict-item]
    agent = AISoftwareEngineerAgent(llm=MagicMock())
    with pytest.raises(ValueError, match="requirements"):
        agent.run(sample_state)


# ---------------------------------------------------------------------------
# Routing unit tests
# ---------------------------------------------------------------------------


def test_router_backend_routes_to_ase():
    """WorkflowRouter: BACKEND_ENGINEERING routes to AI_SOFTWARE_ENGINEERING."""
    from app.router import WorkflowRouter
    from typing import cast

    state = cast(
        ForgeState,
        {
            "user_request": "test",
            "current_stage": WorkflowStages.BACKEND_ENGINEERING,
            "approval_status": ApprovalStatuses.APPROVED,
            "messages": [],
            "metadata": {},
        },
    )
    assert WorkflowRouter.get_next_stage(state) == WorkflowStages.AI_SOFTWARE_ENGINEERING


def test_router_ase_routes_to_final_report():
    """WorkflowRouter: AI_SOFTWARE_ENGINEERING routes to FINAL_REPORT_GENERATION."""
    from app.router import WorkflowRouter
    from typing import cast

    state = cast(
        ForgeState,
        {
            "user_request": "test",
            "current_stage": WorkflowStages.AI_SOFTWARE_ENGINEERING,
            "approval_status": ApprovalStatuses.APPROVED,
            "messages": [],
            "metadata": {},
        },
    )
    assert WorkflowRouter.get_next_stage(state) == WorkflowStages.FINAL_REPORT_GENERATION


# ---------------------------------------------------------------------------
# End-to-end integration test
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_all_llms():
    """Mock LLMs for every agent in the pipeline."""
    with (
        patch("agents.engineering_manager.agent.get_llm") as mock_em,
        patch("agents.requirement_analyst.agent.get_llm") as mock_ra,
        patch("agents.solution_architect.agent.get_llm") as mock_sa,
        patch("agents.backend_engineer.agent.get_llm") as mock_be,
        patch("agents.ai_software_engineer.agent.get_llm") as mock_ase,
    ):
        em = MagicMock()
        em.invoke.return_value = AIMessage(content="EM plan", name="engineering_manager")
        mock_em.return_value = em

        ra = MagicMock()
        ra.invoke.return_value = AIMessage(
            content="# Overview\n\nRequirements.", name="requirement_analyst"
        )
        mock_ra.return_value = ra

        sa = MagicMock()
        sa.invoke.return_value = AIMessage(
            content="# Architecture\n\n# Architecture Pattern\nModular Monolith\n"
            "# Technology Stack\n- **Database**: PostgreSQL\n- **Authentication**: JWT\n"
            "# API Design\nGET /api/v1/items\n# Scalability Strategy\nHorizontal",
            name="solution_architect",
        )
        mock_sa.return_value = sa

        be = MagicMock()
        be.invoke.return_value = AIMessage(
            content="# Backend Blueprint\n\nControllers: ItemController.",
            name="backend_engineer",
        )
        mock_be.return_value = be

        ase = MagicMock()
        ase.invoke.return_value = AIMessage(
            content=MINIMAL_WORKSPACE_JSON,
            name="ai_software_engineer",
        )
        mock_ase.return_value = ase

        yield {"em": em, "ra": ra, "sa": sa, "be": be, "ase": ase}


def test_full_pipeline_approved(tmp_path, mock_all_llms):
    """Full pipeline: EM→RA→SA→HUMAN_APPROVAL→BE→ASE→END with approval."""
    with patch("app.settings.settings.ARTIFACT_ROOT", new=str(tmp_path)):
        workflow = ForgeWorkflow(approval_interface=SimulatedApproval(ApprovalStatuses.APPROVED))
        final_state = workflow.execute("Build a bookstore REST API")

    # Final stage
    assert final_state["current_stage"] == WorkflowStages.FINAL_REPORT_GENERATION
    assert final_state["approval_status"] == ApprovalStatuses.APPROVED

    # Messages: EM, RA, SA, BE, ASE
    assert len(final_state["messages"]) == 5
    names = [m.name for m in final_state["messages"]]
    assert names == [
        "engineering_manager",
        "requirement_analyst",
        "solution_architect",
        "backend_engineer",
        "ai_software_engineer",
    ]

    # generated_files populated
    assert isinstance(final_state["generated_files"], dict)
    assert "src/main.py" in final_state["generated_files"]
    assert len(final_state["generated_files"]) == len(MINIMAL_WORKSPACE)

    # Artifacts registered
    assert "implementation" in final_state["artifacts"]
    assert "backend" in final_state["artifacts"]
    assert "requirements" in final_state["artifacts"]

    # Files exist on disk
    generated_base = os.path.join(str(tmp_path), "implementation", "generated")
    assert os.path.isdir(generated_base)
    for rel_path in MINIMAL_WORKSPACE:
        assert os.path.exists(os.path.join(generated_base, rel_path))

    # Metadata
    assert final_state["metadata"]["ai_software_engineering_completed"] is True


def test_full_pipeline_rejected(tmp_path, mock_all_llms):
    """Pipeline terminates at HUMAN_APPROVAL when rejected — ASE never runs."""
    with patch("app.settings.settings.ARTIFACT_ROOT", new=str(tmp_path)):
        workflow = ForgeWorkflow(
            approval_interface=SimulatedApproval(ApprovalStatuses.REJECTED, "Not good")
        )
        final_state = workflow.execute("Build a bookstore REST API")

    assert final_state["current_stage"] == WorkflowStages.HUMAN_APPROVAL
    assert final_state["approval_status"] == ApprovalStatuses.REJECTED
    # ASE never ran → generated_files empty
    assert final_state.get("generated_files") == {}
    # ASE message not present
    names = [m.name for m in final_state["messages"]]
    assert "ai_software_engineer" not in names
