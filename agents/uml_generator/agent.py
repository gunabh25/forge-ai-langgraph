"""UML Generator Agent implementation.

Pipeline per diagram (sequential, free-tier optimized):
    1. Planning  — LLM scopes actors, components, and flow.
    2. Generation — LLM produces PlantUML from Business Summary + Plan.
    3. Local syntax validation — subprocess plantuml check, zero LLM cost.
    4. Review    — LLM self-evaluates, ONLY if syntax validation passed.
    5. Retry (once) — if review fails, regenerate with issue context.
    6. Skip review — if syntax validation fails (diagram goes to UML Repair Agent).

Max LLM calls per diagram (syntax valid, review passes)   : 3 (plan + generate + review)
Max LLM calls per diagram (syntax valid, review fails)    : 4 (plan + generate + review + regen)
Max LLM calls per diagram (syntax invalid)                : 2 (plan + generate) — review skipped
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.base import BaseAgent
from agents.uml_generator.context_builder import ContextBuilder
from agents.uml_generator.diagram_constraints import get_constraints
from agents.uml_generator.prompt_builder import PromptBuilder
from app.state import ForgeState
from config.logging import get_logger
from core.agent_registry import AgentRegistry
from core.artifact_manager import ArtifactManager
from core.llm import get_llm
from core.utils import generate_timestamp

logger = get_logger("agents.uml_generator")


# ---------------------------------------------------------------------------
# Shared system prompt for ancillary LLM calls (planning & review)
# ---------------------------------------------------------------------------

_ARCHITECT_SYSTEM = (
    "You are a Principal Software Architect with deep expertise in UML and "
    "system design. You produce concise, accurate outputs in the format "
    "requested — never adding invented components or services."
)


# ---------------------------------------------------------------------------
# Execution metrics accumulator
# ---------------------------------------------------------------------------

class _Metrics:
    """Lightweight call counter for a single UMLGeneratorAgent.run() invocation."""

    __slots__ = ("planning_calls", "generation_calls", "review_calls", "repair_calls")

    def __init__(self) -> None:
        self.planning_calls = 0
        self.generation_calls = 0
        self.review_calls = 0
        self.repair_calls = 0  # populated externally by UML Repair Agent

    @property
    def total(self) -> int:
        return self.planning_calls + self.generation_calls + self.review_calls + self.repair_calls

    def as_dict(self) -> dict[str, int]:
        return {
            "planning_calls": self.planning_calls,
            "generation_calls": self.generation_calls,
            "review_calls": self.review_calls,
            "repair_calls": self.repair_calls,
            "total_llm_calls": self.total,
        }


class UMLGeneratorAgent(BaseAgent):
    """UML Generator agent responsible for creating PlantUML diagrams."""

    @property
    def name(self) -> str:
        return "UML Generator"

    @property
    def description(self) -> str:
        return "Generates PlantUML syntax for various diagram types based on the user prompt."

    @property
    def capabilities(self) -> List[str]:
        return ["Component", "Sequence", "Activity", "Deployment", "Class", "Use Case"]

    @property
    def requires(self) -> List[str]:
        return ["architecture_json", "selected_uml_diagrams"]

    @property
    def produces(self) -> List[str]:
        return ["plantuml_diagrams"]

    def __init__(self, llm: Optional[BaseChatModel] = None) -> None:
        self._llm = llm
        self.artifact_manager = ArtifactManager()
        self.context_builder = ContextBuilder()
        self.prompt_builder = PromptBuilder()

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    # -----------------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------------

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the UML Generator agent step."""
        user_request = state.get("user_request", "").strip()
        architecture_json = state.get("architecture_json") or {}
        selected_uml_diagrams = state.get("selected_uml_diagrams", []) or []
        current_diagram_id = state.get("current_diagram_id")

        if not selected_uml_diagrams:
            logger.warning("No UML diagrams selected for generation.")
            return {}

        # Respect explicit requested_diagrams from metadata — filter the
        # selected list to only what the caller requested.
        metadata = state.get("metadata", {}) or {}
        requested_diagrams: List[str] = metadata.get("requested_diagrams", []) or []
        if requested_diagrams:
            requested_lower = {d.lower() for d in requested_diagrams}
            filtered = [
                d for d in selected_uml_diagrams
                if d.get("diagram", "").lower() in requested_lower
                or d.get("diagram_id", "").lower() in requested_lower
            ]
            if filtered:
                selected_uml_diagrams = filtered
                logger.info(
                    "Filtered selected_uml_diagrams to explicit request | "
                    "requested=%s | remaining=%d",
                    requested_diagrams,
                    len(filtered),
                )

        if current_diagram_id:
            diagrams_to_process = [
                d for d in selected_uml_diagrams
                if d.get("diagram_id", d.get("diagram", d.get("type", "unknown"))) == current_diagram_id
            ]
            logger.info(
                "UML Generator starting parallel generation | diagram_id=%s",
                current_diagram_id,
            )
        else:
            diagrams_to_process = selected_uml_diagrams
            logger.info(
                "UML Generator starting sequential generation | count=%d",
                len(selected_uml_diagrams),
            )

        # Initialize from existing state
        diagrams = dict(state.get("plantuml_diagrams", {}) or {})
        saved_paths = list(state.get("artifacts", {}).get("uml", []) or [])
        diagram_states = dict(state.get("diagram_execution_states", {}) or {})

        # Build Business Architecture Summary once — shared across all diagrams.
        architecture_summary: str = (
            state.get("architecture_summary")  # type: ignore[assignment]
            or self.context_builder.build_summary(architecture_json)
        )
        logger.info(
            "Architecture summary ready | summary_len=%d",
            len(architecture_summary),
        )

        metrics = _Metrics()

        for diagram_info in diagrams_to_process:
            diagram_type = diagram_info.get("diagram", diagram_info.get("type", "unknown"))
            diag_id = diagram_info.get("diagram_id", diagram_type)
            reason = diagram_info.get("reason", "")

            existing_state = diagram_states.get(diag_id, {})
            if existing_state.get("status") == "success" and existing_state.get("generator_output"):
                logger.info("Cache hit | diagram_id=%s — skipping generation.", diag_id)
                continue

            start_time = time.time()
            diagram_llm_calls = 0

            # -- Step 1: Planning ------------------------------------------------
            diagram_plan = self._plan_diagram(
                diagram_type=diagram_type,
                architecture_summary=architecture_summary,
                user_request=user_request,
            )
            metrics.planning_calls += 1
            diagram_llm_calls += 1

            # -- Step 2: Generation ----------------------------------------------
            system_prompt, user_prompt = self.prompt_builder.build_prompt(
                diagram_type=diagram_type,
                architecture_summary=architecture_summary,
                diagram_plan=diagram_plan,
            )
            full_user_prompt = (
                f"User Request: {user_request}\n\n"
                f"Reason for this diagram: {reason}\n\n"
                f"{user_prompt}"
            )

            prompt_length = len(system_prompt) + len(full_user_prompt)
            logger.info(
                "LLM generation starting | "
                "diagram_type=%s | architecture_summary_len=%d | "
                "diagram_plan_len=%d | prompt_length=%d | estimated_token_count=%d",
                diagram_type,
                len(architecture_summary),
                len(diagram_plan),
                prompt_length,
                prompt_length // 4,
            )

            clean_content = self._generate(system_prompt, full_user_prompt)
            metrics.generation_calls += 1
            diagram_llm_calls += 1

            # -- Step 3: Local syntax validation (no LLM) ------------------------
            syntax_valid = self._validate_syntax_locally(clean_content, diagram_type)

            if syntax_valid:
                # -- Step 4: Review (only when syntax is valid) ------------------
                constraints = get_constraints(diagram_type)
                review = self._review_diagram(diagram_type, clean_content, constraints)
                metrics.review_calls += 1
                diagram_llm_calls += 1

                if not review.get("acceptable", True):
                    issues_text = "; ".join(review.get("issues", []))
                    logger.warning(
                        "Diagram review failed — regenerating once | "
                        "diagram_type=%s | issues=%s",
                        diagram_type,
                        issues_text,
                    )
                    retry_prompt = (
                        f"{full_user_prompt}\n\n"
                        f"## Quality Review Feedback\n\n"
                        f"A previous attempt was rejected for the following reasons. "
                        f"Fix all of them in this regeneration:\n"
                        + "\n".join(f"- {issue}" for issue in review.get("issues", []))
                    )
                    clean_content = self._generate(system_prompt, retry_prompt)
                    metrics.generation_calls += 1
                    diagram_llm_calls += 1
                    logger.info("Diagram regenerated after review | diagram_type=%s", diagram_type)
                else:
                    logger.info("Diagram review passed | diagram_type=%s", diagram_type)
            else:
                logger.warning(
                    "Diagram has syntax errors — skipping review, sending to Repair Agent | "
                    "diagram_type=%s",
                    diagram_type,
                )

            generation_time_ms = int((time.time() - start_time) * 1000)

            # -- Persist ----------------------------------------------------------
            diagrams[diag_id] = clean_content

            base_name = diag_id.lower().replace(" ", "_")
            saved_path = self.artifact_manager.save_artifact(
                stage="uml",
                base_name=base_name,
                content=clean_content,
                ext="puml",
            )
            if saved_path not in saved_paths:
                saved_paths.append(saved_path)

            diagram_states[diag_id] = {
                "diagram_id": diag_id,
                "diagram_type": diagram_type,
                "status": "generated",
                "attempt": existing_state.get("attempt", 0) + 1,
                "generator_output": clean_content,
                "execution_time_ms": existing_state.get("execution_time_ms", 0) + generation_time_ms,
                "llm_calls": existing_state.get("llm_calls", 0) + diagram_llm_calls,
                "syntax_valid_at_generation": syntax_valid,
            }

        # -- Emit execution metrics -------------------------------------------
        self._log_metrics(metrics, len(diagrams_to_process))

        new_message = AIMessage(
            content=f"Generated {len(diagrams_to_process)} diagram(s).",
            name="uml_generator",
        )

        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "uml_generation_completed": True,
            "uml_llm_metrics": metrics.as_dict(),
            "last_updated": generate_timestamp(),
        }

        return {
            "plantuml_diagrams": diagrams,
            "diagram_execution_states": diagram_states,
            "artifacts": {"uml": saved_paths},
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_generator",
            "architecture_summary": architecture_summary,
        }

    # -----------------------------------------------------------------------
    # Planning step
    # -----------------------------------------------------------------------

    def _plan_diagram(
        self,
        diagram_type: str,
        architecture_summary: str,
        user_request: str,
    ) -> str:
        """Produce a scoped diagram plan before PlantUML generation."""
        planning_prompt = (
            f"You are preparing to generate a **{diagram_type} Diagram** for "
            f"the following system.\n\n"
            f"## Business Architecture Summary\n\n"
            f"{architecture_summary}\n\n"
            f"## User Request\n\n"
            f"{user_request}\n\n"
            f"## Task\n\n"
            f"Before generating any PlantUML, produce a concise diagram plan "
            f"that identifies ONLY the elements to include. Use ONLY what is "
            f"explicitly present in the architecture summary above — do NOT "
            f"invent any services, gateways, or infrastructure.\n\n"
            f"Format your response as:\n\n"
            f"**Actors**: <comma-separated list>\n"
            f"**External Systems**: <comma-separated list or 'None'>\n"
            f"**Major Components**: <comma-separated list, max 8>\n"
            f"**Primary Business Flow**: <one sentence describing the main flow>\n"
            f"**Diagram Scope**: <one sentence stating what this diagram shows and what it excludes>\n\n"
            f"Respond with ONLY the plan in the format above. No PlantUML. No extra commentary."
        )

        messages = [
            SystemMessage(content=_ARCHITECT_SYSTEM),
            HumanMessage(content=planning_prompt),
        ]

        logger.info(
            "LLM planning starting | diagram_type=%s | planning_prompt_len=%d",
            diagram_type,
            len(planning_prompt),
        )

        try:
            response = self.llm.invoke(messages)
            plan = str(response.content).strip()
            logger.info(
                "LLM planning completed | diagram_type=%s | plan_len=%d",
                diagram_type,
                len(plan),
            )
            return plan
        except Exception as exc:
            logger.warning(
                "Planning step failed — proceeding without plan | diagram_type=%s | error=%s",
                diagram_type,
                exc,
            )
            return ""

    # -----------------------------------------------------------------------
    # Local syntax validation (no LLM cost)
    # -----------------------------------------------------------------------

    def _validate_syntax_locally(self, plantuml_content: str, diagram_type: str) -> bool:
        """Run a local PlantUML syntax check using the plantuml binary.

        This is a zero-LLM-cost check. If the plantuml binary is unavailable,
        falls back to a heuristic structural check so we never block generation.

        Returns:
            True if syntax appears valid, False if an error is detected.
        """
        # Heuristic guard: must start with @startuml and end with @enduml.
        content = plantuml_content.strip()
        if not (content.startswith("@startuml") and content.endswith("@enduml")):
            logger.warning(
                "Local syntax heuristic failed (missing @startuml/@enduml) | diagram_type=%s",
                diagram_type,
            )
            return False

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".puml",
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            result = subprocess.run(
                ["plantuml", "-syntax", tmp_path],
                capture_output=True,
                text=True,
                timeout=15,
            )
            os.unlink(tmp_path)

            has_error = "Error" in result.stdout or "error" in result.stdout.lower()
            if has_error:
                logger.warning(
                    "Local syntax validation: FAILED | diagram_type=%s | plantuml_output=%s",
                    diagram_type,
                    result.stdout[:300],
                )
                return False

            logger.info(
                "Local syntax validation: PASSED | diagram_type=%s", diagram_type
            )
            return True

        except FileNotFoundError:
            # plantuml binary not on PATH — fall back to heuristic (already passed above)
            logger.info(
                "plantuml binary not found — using heuristic validation only | diagram_type=%s",
                diagram_type,
            )
            return True
        except Exception as exc:
            logger.warning(
                "Local syntax validation error — assuming valid | diagram_type=%s | error=%s",
                diagram_type,
                exc,
            )
            return True

    # -----------------------------------------------------------------------
    # Review step (LLM — only called when syntax is valid)
    # -----------------------------------------------------------------------

    def _review_diagram(
        self,
        diagram_type: str,
        plantuml_content: str,
        constraints: dict[str, Any],
    ) -> dict[str, Any]:
        """Self-review the generated PlantUML against quality criteria.

        Only called when local syntax validation has already passed.
        """
        constraint_lines = "\n".join(
            f"- {k.replace('_', ' ')}: {v}" for k, v in constraints.items()
        ) or "No specific constraints."

        review_prompt = (
            f"You are reviewing a generated **{diagram_type} Diagram** "
            f"(PlantUML) for architecture-review quality.\n\n"
            f"## Diagram Constraints\n{constraint_lines}\n\n"
            f"## Generated PlantUML\n\n"
            f"```\n{plantuml_content}\n```\n\n"
            f"## Review Criteria\n\n"
            f"Evaluate the diagram on each of the following criteria:\n"
            f"1. **Abstraction level** — Does it stay at the correct business/architecture level? "
            f"No implementation details (repositories, helpers, internals)?\n"
            f"2. **Component count** — Does it respect the constraint limits?\n"
            f"3. **Arrow density** — Are connections clear and not overwhelming?\n"
            f"4. **No implementation leakage** — Are there any utility classes, "
            f"DAOs, middleware, or internal helpers present?\n"
            f"5. **Business flow present** — Does the diagram communicate the "
            f"business purpose clearly?\n"
            f"6. **No hallucinated services** — Does it contain any services "
            f"(e.g. API Gateway, Auth Service, Notification Service) that were "
            f"not explicitly described in the architecture context?\n\n"
            f"## Response Format\n\n"
            f"Respond with ONLY valid JSON in exactly this structure — no markdown fences:\n"
            f"{{\n"
            f'  "acceptable": true,\n'
            f'  "issues": []\n'
            f"}}\n\n"
            f"Set ``acceptable`` to ``false`` and list specific issues if any "
            f"criterion fails. Be strict — this diagram will be shown in a "
            f"Senior Architect review."
        )

        messages = [
            SystemMessage(content=_ARCHITECT_SYSTEM),
            HumanMessage(content=review_prompt),
        ]

        logger.info(
            "LLM review starting | diagram_type=%s | plantuml_len=%d",
            diagram_type,
            len(plantuml_content),
        )

        try:
            response = self.llm.invoke(messages)
            raw = str(response.content).replace("```json", "").replace("```", "").strip()
            result: dict[str, Any] = json.loads(raw)
            logger.info(
                "LLM review completed | diagram_type=%s | acceptable=%s | issue_count=%d",
                diagram_type,
                result.get("acceptable"),
                len(result.get("issues", [])),
            )
            return result
        except Exception as exc:
            logger.warning(
                "Review step failed — treating as acceptable | diagram_type=%s | error=%s",
                diagram_type,
                exc,
            )
            return {"acceptable": True, "issues": []}

    # -----------------------------------------------------------------------
    # Shared generation helper
    # -----------------------------------------------------------------------

    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke the LLM and return clean PlantUML content."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = self.llm.invoke(messages)
        return (
            str(response.content)
            .replace("```plantuml", "")
            .replace("```puml", "")
            .replace("```", "")
            .strip()
        )

    # -----------------------------------------------------------------------
    # Metrics logging
    # -----------------------------------------------------------------------

    def _log_metrics(self, metrics: _Metrics, diagram_count: int) -> None:
        """Log per-workflow LLM call breakdown and total."""
        separator = "=" * 52
        logger.info(separator)
        logger.info(
            "UML Generator — LLM Call Metrics | diagrams=%d", diagram_count
        )
        logger.info("  planning_calls   : %d", metrics.planning_calls)
        logger.info("  generation_calls : %d", metrics.generation_calls)
        logger.info("  review_calls     : %d", metrics.review_calls)
        logger.info("  repair_calls     : %d (populated by Repair Agent)", metrics.repair_calls)
        logger.info("  ─────────────────────────────────────")
        logger.info("  TOTAL LLM CALLS  : %d", metrics.total)
        logger.info(separator)
        # Also print to stdout so it's visible in the CLI
        print(f"\n{'=' * 52}")
        print(f"  UML LLM Metrics ({diagram_count} diagram(s))")
        print(f"  Planning calls   : {metrics.planning_calls}")
        print(f"  Generation calls : {metrics.generation_calls}")
        print(f"  Review calls     : {metrics.review_calls}")
        print(f"  {'─' * 38}")
        print(f"  TOTAL (generator): {metrics.total}")
        print(f"{'=' * 52}\n")


# Automatically register the agent
AgentRegistry().register(UMLGeneratorAgent())
