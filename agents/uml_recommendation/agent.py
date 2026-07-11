"""UML Recommendation Agent implementation.

When the API caller explicitly provides ``diagram_types`` (surfaced in
``state["metadata"]["requested_diagrams"]``), this agent short-circuits the
LLM call entirely and directly constructs ``selected_uml_diagrams`` from the
explicit list. This respects the caller's intent and saves an LLM call.

When no explicit types are provided, the agent falls back to LLM-driven
reasoning — but sends only the Business Architecture Summary (not the full
raw ``architecture_json``) to minimize token usage.
"""

import json
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.base import BaseAgent
from app.state import ForgeState
from config.logging import get_logger
from core.agent_registry import AgentRegistry
from core.llm import get_llm
from core.utils import generate_timestamp

logger = get_logger("agents.uml_recommendation")


class UMLRecommendationAgent(BaseAgent):
    """Recommends necessary UML diagrams with AI-driven reasoning."""

    @property
    def name(self) -> str:
        return "UML Recommendation Agent"

    @property
    def description(self) -> str:
        return (
            "Analyzes architecture and determines strictly which UML diagrams "
            "are required with deep reasoning."
        )

    @property
    def capabilities(self) -> List[str]:
        return ["uml_recommendation", "architecture_reasoning"]

    @property
    def requires(self) -> List[str]:
        return ["architecture_json", "requirements_json"]

    @property
    def produces(self) -> List[str]:
        return ["selected_uml_diagrams"]

    def __init__(self, llm: Optional[BaseChatModel] = None) -> None:
        self._llm = llm

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    # -----------------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------------

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the UML Recommendation Agent.

        Short-circuits to explicit-selection mode when the caller has already
        specified diagram types via ``state["metadata"]["requested_diagrams"]``.
        """
        logger.info("UML Recommendation Agent starting execution.")

        metadata = state.get("metadata", {}) or {}
        requested_diagrams: List[str] = metadata.get("requested_diagrams", []) or []

        # -- Task 5: Honour explicit diagram_types from the API caller ---------
        if requested_diagrams:
            return self._build_from_explicit_selection(state, requested_diagrams)

        # -- LLM-driven recommendation (fallback) ------------------------------
        return self._build_from_llm(state)

    # -----------------------------------------------------------------------
    # Explicit selection path (Task 5)
    # -----------------------------------------------------------------------

    def _build_from_explicit_selection(
        self,
        state: ForgeState,
        requested_diagrams: List[str],
    ) -> Dict[str, Any]:
        """Build selected_uml_diagrams directly from the caller's explicit list.

        No LLM call is made. Each entry in the output list is constructed with
        a ``diagram_id`` and a neutral reason string.
        """
        logger.info(
            "Explicit diagram_types provided — skipping LLM call | types=%s",
            requested_diagrams,
        )

        selected_diagrams = [
            {
                "diagram": dtype.strip(),
                "diagram_id": dtype.strip().lower().replace(" ", "_"),
                "reason": "Explicitly requested by the caller.",
                "priority": "High",
                "confidence": 1.0,
            }
            for dtype in requested_diagrams
            if dtype.strip()
        ]

        recommendation_report: Dict[str, Any] = {
            "selected_diagrams": selected_diagrams,
            "rejected_diagrams": [],
            "selection_mode": "explicit",
        }

        logger.info(
            "Explicit selection complete | diagram_count=%d",
            len(selected_diagrams),
        )

        new_message = AIMessage(
            content=json.dumps(recommendation_report, indent=2),
            name="uml_recommendation",
        )

        current_metadata = state.get("metadata", {}) or {}
        return {
            "uml_recommendation_report": recommendation_report,
            "selected_uml_diagrams": selected_diagrams,
            "messages": [new_message],
            "metadata": {
                **current_metadata,
                "uml_recommendation_completed": True,
                "uml_recommendation_mode": "explicit",
                "last_updated": generate_timestamp(),
            },
            "current_stage": "uml_recommendation",
        }

    # -----------------------------------------------------------------------
    # LLM-driven recommendation path (Task 6: use summary not raw JSON)
    # -----------------------------------------------------------------------

    def _build_from_llm(self, state: ForgeState) -> Dict[str, Any]:
        """Use LLM reasoning to recommend diagram types.

        Token reduction (Task 6): The LLM receives the Business Architecture
        Summary (if already built) instead of the full raw ``architecture_json``.
        This avoids sending hundreds of tokens of implementation-level detail
        that would only introduce noise into the recommendation.
        """
        user_request = state.get("user_request", "")
        requirements_json = state.get("requirements_json", {})

        # Prefer the pre-built summary (set by UMLGeneratorAgent if it ran
        # first, or by any other pre-processing step).
        architecture_context = state.get("architecture_summary") or ""
        if not architecture_context:
            # Fall back to raw JSON only when no summary is available.
            architecture_json = state.get("architecture_json", {})
            architecture_context = (
                json.dumps(architecture_json, indent=2)
                if architecture_json
                else "No architecture details provided."
            )
            logger.info(
                "architecture_summary not in state — falling back to raw JSON "
                "for recommendation | json_len=%d",
                len(architecture_context),
            )
        else:
            logger.info(
                "Using pre-built architecture_summary for recommendation | "
                "summary_len=%d",
                len(architecture_context),
            )

        system_prompt = """You are a Principal Software Architect.
Read the provided requirements and architecture description.
Reason over the system boundaries, communication, deployment, and state to decide
exactly which UML diagrams are required to visualize it properly.

Supported UML: Use Case, Activity, Sequence, Communication, Class, Object,
Component, Deployment, Package, Composite Structure, State Machine, Timing,
Interaction Overview, Profile.

You MUST NOT hardcode rules. Use deep architectural reasoning.
Only recommend diagrams that provide real value. Do not automatically generate all UML diagrams.

Output ONLY valid JSON matching this exact structure:
{
    "selected_diagrams": [
        {
            "diagram": "Diagram Name",
            "reason": "Explicit architectural reason based on boundaries, communication, deployment, or state.",
            "priority": "High|Medium|Low",
            "confidence": 0.95
        }
    ],
    "rejected_diagrams": [
        {
            "diagram": "Diagram Name",
            "reason": "Explicit reason why it is unnecessary."
        }
    ]
}

DO NOT include markdown tags or explanation. Output ONLY the JSON.
"""

        human_content = (
            f"User Request: {user_request}\n\n"
            f"Requirements JSON:\n{json.dumps(requirements_json, indent=2)}\n\n"
            f"Architecture Summary:\n{architecture_context}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_content),
        ]

        logger.info(
            "Invoking LLM for UML Recommendation | "
            "context_len=%d",
            len(human_content),
        )
        llm_response = self.llm.invoke(messages)

        response_content = (
            str(llm_response.content).replace("```json", "").replace("```", "").strip()
        )

        try:
            recommendation_report = json.loads(response_content)
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse JSON from recommendation response | preview=%s",
                response_content[:200],
            )
            recommendation_report = {"selected_diagrams": [], "rejected_diagrams": []}

        selected = recommendation_report.get("selected_diagrams", [])
        logger.info(
            "UML Recommendation generated | selected_count=%d",
            len(selected),
        )

        new_message = AIMessage(
            content=json.dumps(recommendation_report, indent=2),
            name="uml_recommendation",
        )

        current_metadata = state.get("metadata", {}) or {}
        return {
            "uml_recommendation_report": recommendation_report,
            "selected_uml_diagrams": selected,
            "messages": [new_message],
            "metadata": {
                **current_metadata,
                "uml_recommendation_completed": True,
                "uml_recommendation_mode": "llm",
                "last_updated": generate_timestamp(),
            },
            "current_stage": "uml_recommendation",
        }


AgentRegistry().register(UMLRecommendationAgent())
