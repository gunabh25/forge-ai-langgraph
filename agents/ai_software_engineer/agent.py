"""AI Software Engineer Agent implementation.

This agent generates a complete virtual project workspace from the approved
Backend Blueprint. It produces individual source files (controllers, services,
repositories, models, middleware, routes, configuration, tests, Dockerfile,
README, etc.) and writes each one to disk under the artifact directory.
"""

import json
import os
import re
from typing import Dict, Any, Optional, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.state import ForgeState
from config.logging import get_logger
from core.artifact_manager import ArtifactManager
from core.constants import ArtifactFolders, WorkflowStages
from core.llm import get_llm
from core.prompts import load_prompt, load_examples
from core.utils import ensure_directory, generate_timestamp, safe_write_file

logger = get_logger("agents.ai_software_engineer")

# Sub-folder under the implementation artifact folder that holds generated files
GENERATED_SUBDIR = "generated"


class WorkspaceParser:
    """Parses the LLM response into a workspace file registry.

    The LLM is instructed to respond with a pure JSON object whose keys are
    relative file paths and whose values are the complete source code strings.
    This parser handles:
      - Plain JSON responses
      - JSON wrapped in a markdown code fence (```json ... ```)
    """

    # Pattern to strip a surrounding markdown code fence (optional language tag)
    _FENCE_PATTERN = re.compile(
        r"^\s*```[a-zA-Z0-9_-]*\s*\n(.*?)\n\s*```\s*$",
        re.DOTALL,
    )

    @classmethod
    def extract(cls, llm_response: str) -> Dict[str, str]:
        """Parse LLM response into a ``{relative_path: source_code}`` dict.

        Args:
            llm_response: Raw string content from the LLM.

        Returns:
            Dictionary mapping relative file paths to source code strings.

        Raises:
            ValueError: If the response cannot be parsed as a valid workspace
                JSON object, or if any value is not a string.
        """
        raw = llm_response.strip()

        # Strip markdown code fence if present
        fence_match = cls._FENCE_PATTERN.match(raw)
        if fence_match:
            raw = fence_match.group(1).strip()

        # Locate the outermost JSON object — handles any leading/trailing prose
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(
                "AI Software Engineer: LLM response does not contain a JSON object. "
                f"Response preview: {raw[:300]!r}"
            )
        raw = raw[start : end + 1]

        try:
            workspace: Any = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"AI Software Engineer: Failed to parse LLM response as JSON: {exc}. "
                f"Response preview: {raw[:300]!r}"
            ) from exc

        if not isinstance(workspace, dict):
            raise ValueError(
                f"AI Software Engineer: Expected a JSON object at the top level, "
                f"got {type(workspace).__name__}."
            )

        # Validate all values are strings
        invalid_keys = [k for k, v in workspace.items() if not isinstance(v, str)]
        if invalid_keys:
            raise ValueError(
                f"AI Software Engineer: Workspace JSON has non-string values for "
                f"keys: {invalid_keys}. Each value must be a source code string."
            )

        if not workspace:
            raise ValueError(
                "AI Software Engineer: LLM returned an empty workspace JSON object."
            )

        return workspace


class AISoftwareEngineerAgent:
    """AI Software Engineer agent that generates a complete project workspace.

    Reads ``requirements``, ``architecture``, and ``backend_blueprint`` from the
    shared ForgeState, prompts the LLM to generate a full JSON workspace, writes
    every file to disk, and returns updated state slices including
    ``generated_files``, ``artifacts``, ``implementation``, and ``messages``.

    Construction supports dependency injection of a mock LLM for testing. The
    real LLM is lazily instantiated on first access via the ``llm`` property,
    preventing Pydantic validation errors when no API key is present during tests.
    """

    def __init__(self, llm: Optional[BaseChatModel] = None) -> None:
        """Initialise the agent.

        Args:
            llm: Optional LLM instance. If ``None``, the default LLM is lazily
                loaded from ``core.llm.get_llm`` on first use.
        """
        self._llm = llm
        self.system_prompt = load_prompt("ai_software_engineer")
        try:
            self.examples = load_examples("ai_software_engineer")
        except FileNotFoundError:
            self.examples = ""
        self.artifact_manager = ArtifactManager()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def llm(self) -> BaseChatModel:
        """Lazily instantiated LLM — safe for test environments without API keys."""
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the AI Software Engineer agent step.

        Args:
            state: The current shared ForgeState.

        Returns:
            Dictionary of state updates to be merged by LangGraph reducers.

        Raises:
            ValueError: If required upstream artifacts (requirements, architecture,
                backend_blueprint) are missing from state.
        """
        logger.info("Implementation started")

        # ── Validate required inputs ─────────────────────────────────────────
        requirements: str = (state.get("requirements") or "").strip()
        architecture: str = (state.get("architecture") or "").strip()
        backend_blueprint: str = (state.get("backend_blueprint") or "").strip()

        missing = [
            name
            for name, val in [
                ("requirements", requirements),
                ("architecture", architecture),
                ("backend_blueprint", backend_blueprint),
            ]
            if not val
        ]
        if missing:
            raise ValueError(
                f"AI Software Engineer: Missing required state fields: {missing}"
            )

        # ── Build prompt messages ─────────────────────────────────────────────
        prompt_content = self.system_prompt
        if self.examples:
            prompt_content += (
                "\n\nHere are examples of the expected JSON workspace output:\n"
                + self.examples
            )

        human_content = (
            f"Requirements Specification:\n{requirements}\n\n"
            f"Architecture Specification:\n{architecture}\n\n"
            f"Backend Blueprint:\n{backend_blueprint}"
        )

        messages = [
            SystemMessage(content=prompt_content),
            HumanMessage(content=human_content),
        ]

        # ── Invoke LLM ───────────────────────────────────────────────────────
        logger.info("Workspace generation started")
        llm_response = self.llm.invoke(messages)

        raw_content: str = llm_response.content  # type: ignore[assignment]
        if isinstance(raw_content, list):
            raw_content = "\n".join(str(item) for item in raw_content)
        else:
            raw_content = str(raw_content)

        # ── Parse workspace JSON ──────────────────────────────────────────────
        workspace: Dict[str, str] = WorkspaceParser.extract(raw_content)
        file_count = len(workspace)
        logger.info(f"Files generated", extra={"file_count": file_count})

        # ── Write files to disk ───────────────────────────────────────────────
        saved_file_paths = self._write_workspace(workspace)
        logger.info("Workspace saved", extra={"saved_paths": len(saved_file_paths)})

        # ── Register implementation artifact (manifest file) ─────────────────
        manifest_content = self._build_manifest(workspace, saved_file_paths)
        manifest_path = self.artifact_manager.save_artifact(
            stage=ArtifactFolders.IMPLEMENTATION,
            base_name="implementation_manifest",
            content=manifest_content,
            ext="md",
        )

        # ── Build state updates ───────────────────────────────────────────────
        summary_lines: List[str] = [
            f"Generated {file_count} files:",
            *[f"  • {path}" for path in sorted(workspace.keys())[:20]],
        ]
        if file_count > 20:
            summary_lines.append(f"  … and {file_count - 20} more files")
        implementation_summary = "\n".join(summary_lines)

        new_message = AIMessage(
            content=implementation_summary,
            name="ai_software_engineer",
        )

        current_metadata: Dict[str, Any] = dict(state.get("metadata") or {})
        updated_metadata: Dict[str, Any] = {
            **current_metadata,
            "ai_software_engineering_completed": True,
            "generated_file_count": file_count,
            "last_updated": generate_timestamp(),
        }

        state_updates: Dict[str, Any] = {
            "implementation": implementation_summary,
            "generated_files": workspace,
            "artifacts": {
                ArtifactFolders.IMPLEMENTATION: [manifest_path] + saved_file_paths
            },
            "current_stage": WorkflowStages.AI_SOFTWARE_ENGINEERING,
            "messages": [new_message],
            "metadata": updated_metadata,
        }

        logger.info("Implementation completed")
        return state_updates

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _write_workspace(self, workspace: Dict[str, str]) -> List[str]:
        """Write all workspace files to disk and return absolute paths.

        Files are written to:
            ``<artifact_root>/implementation/generated/<relative_path>``

        Args:
            workspace: Mapping of relative file paths to source code strings.

        Returns:
            List of absolute paths to every written file.
        """
        generated_base = os.path.join(
            self.artifact_manager.get_stage_directory(ArtifactFolders.IMPLEMENTATION),
            GENERATED_SUBDIR,
        )
        ensure_directory(generated_base)

        saved: List[str] = []
        for rel_path, content in workspace.items():
            abs_path = os.path.join(generated_base, rel_path)
            safe_write_file(abs_path, content)
            saved.append(abs_path)
        return saved

    def _build_manifest(
        self, workspace: Dict[str, str], saved_paths: List[str]
    ) -> str:
        """Build a Markdown manifest listing all generated files.

        Args:
            workspace: Relative path → source code mapping.
            saved_paths: Absolute disk paths of the written files.

        Returns:
            Markdown string.
        """
        lines = [
            "# Implementation Manifest",
            "",
            f"**Total files generated**: {len(workspace)}",
            "",
            "## Generated Files",
            "",
        ]
        for rel_path in sorted(workspace.keys()):
            lines.append(f"- `{rel_path}`")
        lines += [
            "",
            "## Artifact Locations",
            "",
            "Files are stored under `artifacts/implementation/generated/`.",
        ]
        return "\n".join(lines)
