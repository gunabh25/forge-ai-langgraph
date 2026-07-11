"""UML Generator Agent implementation.

Pipeline per diagram:
    1. Planning  — LLM scopes actors, components, and flow (prevents hallucination).
    2. Generation — LLM produces PlantUML from Business Summary + Plan.
    3. Review    — LLM self-evaluates against quality criteria.
    4. Retry (once) — if review fails, regenerate with issue context.

Max LLM calls per diagram: 4 (plan + generate + review + optional regeneration).
"""

from __future__ import annotations

import hashlib
import json
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

        arch_str = json.dumps(architecture_json, sort_keys=True)
        arch_hash = hashlib.md5(arch_str.encode("utf-8")).hexdigest()

        # Build Business Architecture Summary once — shared across all diagrams.
        # Prefer a summary already in state (from a previous run) to avoid
        # redundant processing.
        architecture_summary: str = (
            state.get("architecture_summary")  # type: ignore[assignment]
            or self.context_builder.build_summary(architecture_json)
        )
        logger.info(
            "Architecture summary ready | summary_len=%d",
            len(architecture_summary),
        )

        for diagram_info in diagrams_to_process:
            diagram_type = diagram_info.get("diagram", diagram_info.get("type", "unknown"))
            diag_id = diagram_info.get("diagram_id", diagram_type)
            reason = diagram_info.get("reason", "")

            existing_state = diagram_states.get(diag_id, {})
            if existing_state.get("status") == "success" and existing_state.get("generator_output"):
                logger.info("Cache hit | diagram_id=%s — skipping generation.", diag_id)
                continue

            start_time = time.time()

            # -- Step 1: Planning ------------------------------------------------
            diagram_plan = self._plan_diagram(
                diagram_type=diagram_type,
                architecture_summary=architecture_summary,
                user_request=user_request,
            )

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

            # -- Pre-LLM observability -------------------------------------------
            prompt_length = len(system_prompt) + len(full_user_prompt)
            estimated_tokens = prompt_length // 4

            logger.info(
                "LLM generation starting | "
                "diagram_type=%s | "
                "architecture_summary_len=%d | "
                "diagram_plan_len=%d | "
                "prompt_length=%d | "
                "estimated_token_count=%d",
                diagram_type,
                len(architecture_summary),
                len(diagram_plan),
                prompt_length,
                estimated_tokens,
            )

            clean_content = self._generate(system_prompt, full_user_prompt)

            # -- Step 3: Review --------------------------------------------------
            constraints = get_constraints(diagram_type)
            review = self._review_diagram(diagram_type, clean_content, constraints)

            llm_calls = 2  # plan + generate

            if not review.get("acceptable", True):
                issues_text = "; ".join(review.get("issues", []))
                logger.warning(
                    "Diagram review failed — regenerating once | "
                    "diagram_type=%s | issues=%s",
                    diagram_type,
                    issues_text,
                )
                # Single retry: inject issues into the user prompt
                retry_prompt = (
                    f"{full_user_prompt}\n\n"
                    f"## Quality Review Feedback\n\n"
                    f"A previous attempt was rejected for the following reasons. "
                    f"Fix all of them in this regeneration:\n"
                    + "\n".join(f"- {issue}" for issue in review.get("issues", []))
                )
                clean_content = self._generate(system_prompt, retry_prompt)
                llm_calls += 2  # review + regeneration
                logger.info("Diagram regenerated after review | diagram_type=%s", diagram_type)
            else:
                llm_calls += 1  # review only
                logger.info(
                    "Diagram review passed | diagram_type=%s", diagram_type
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

            # Update DiagramExecutionState
            diagram_states[diag_id] = {
                "diagram_id": diag_id,
                "diagram_type": diagram_type,
                "status": "generated",
                "attempt": existing_state.get("attempt", 0) + 1,
                "generator_output": clean_content,
                "execution_time_ms": existing_state.get("execution_time_ms", 0) + generation_time_ms,
                "llm_calls": existing_state.get("llm_calls", 0) + llm_calls,
            }

        new_message = AIMessage(
            content=f"Generated {len(diagrams_to_process)} diagram(s).",
            name="uml_generator",
        )

        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "uml_generation_completed": True,
            "last_updated": generate_timestamp(),
        }

        return {
            "plantuml_diagrams": diagrams,
            "diagram_execution_states": diagram_states,
            "artifacts": {"uml": saved_paths},
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_generator",
            # Surface summary for downstream agents (Task 6 — token reduction)
            "architecture_summary": architecture_summary,
        }

    # -----------------------------------------------------------------------
    # Planning step (Task 3)
    # -----------------------------------------------------------------------

    def _plan_diagram(
        self,
        diagram_type: str,
        architecture_summary: str,
        user_request: str,
    ) -> str:
        """Produce a scoped diagram plan before PlantUML generation.

        The planning LLM call asks the model to enumerate only the elements
        that belong in the requested diagram — actors, external systems,
        major components, the primary business flow, and the diagram scope.
        This explicit scoping step is the primary mechanism for preventing
        hallucination of non-existent services.

        Returns:
            A structured plain-text plan string, or an empty string if the
            planning call fails.
        """
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
    # Review step (Task 4)
    # -----------------------------------------------------------------------

    def _review_diagram(
        self,
        diagram_type: str,
        plantuml_content: str,
        constraints: dict[str, Any],
    ) -> dict[str, Any]:
        """Self-review the generated PlantUML against quality criteria.

        The LLM evaluates six criteria and returns a JSON verdict. If
        ``acceptable`` is False, the caller should regenerate once. This
        method never triggers regeneration itself — it is a pure evaluation.

        Args:
            diagram_type: The diagram type being reviewed.
            plantuml_content: The generated PlantUML string.
            constraints: Per-diagram constraints (from diagram_constraints).

        Returns:
            A dict with keys:
            - ``acceptable`` (bool): True if the diagram passes review.
            - ``issues`` (list[str]): Descriptions of any problems found.
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
            # If review itself fails (parse error, LLM error), treat as acceptable
            # to avoid blocking generation — log prominently.
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


# Automatically register the agent
AgentRegistry().register(UMLGeneratorAgent())
