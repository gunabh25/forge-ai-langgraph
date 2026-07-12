"""UML Repair Agent implementation."""

import time
from typing import Dict, Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from agents.base import BaseAgent
from core.llm import get_llm
from core.agent_registry import AgentRegistry
from app.state import ForgeState
from config.logging import get_logger
from core.utils import generate_timestamp
from core.cost_tracker import record_agent_cost

logger = get_logger("agents.uml_repair")


class UMLRepairAgent(BaseAgent):
    """UML Repair Agent responsible for fixing PlantUML syntax based on compiler errors."""

    @property
    def name(self) -> str:
        return "UML Repair Agent"

    @property
    def description(self) -> str:
        return "Repairs PlantUML syntax errors based on compiler feedback without altering semantics."

    @property
    def capabilities(self) -> List[str]:
        return ["plantuml_repair", "syntax_correction"]

    @property
    def requires(self) -> List[str]:
        return ["plantuml_validation_report", "plantuml_diagrams"]

    @property
    def produces(self) -> List[str]:
        return ["plantuml_diagrams"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the UML Repair Agent step."""
        validation_report = state.get("plantuml_validation_report", {})
        diagrams_content = state.get("plantuml_diagrams", {})
        current_diagram_id = state.get("current_diagram_id")

        if not validation_report or not diagrams_content:
            logger.warning("No validation report or diagrams found for repair.")
            return {}

        diagram_results = validation_report.get("diagram_results", [])
        current_metadata = state.get("metadata", {}) or {}
        diagram_states = dict(state.get("diagram_execution_states", {}) or {})

        # Build the candidate list of failed diagrams.
        if current_diagram_id:
            failed_diagrams = [
                d for d in diagram_results
                if not d.get("valid", True) and d.get("diagram", "") == current_diagram_id
            ]
        else:
            failed_diagrams = [d for d in diagram_results if not d.get("valid", True)]

        # Exclude permanently-failed diagrams — they have already hit MAX_REPAIR_ATTEMPTS
        # and must not consume additional LLM calls.
        failed_diagrams = [
            d for d in failed_diagrams
            if not d.get("permanently_failed", False)
            and diagram_states.get(d.get("diagram", ""), {}).get("status") != "VALIDATION_FAILED"
        ]

        if not failed_diagrams:
            logger.info("No repair-eligible diagrams found. Exiting repair agent.")
            return {}

        logger.info("UML Repair starting execution for %d failed diagrams...", len(failed_diagrams))

        system_prompt = """You are a highly specialized UML Repair Agent.
Your task is to fix PlantUML code based on validation feedback. This feedback may be a syntax error from the compiler OR a semantic failure (e.g. Architecture or Business Flow failure).

Rules:
1. Address the specific errors identified in the validation feedback.
2. If it is a compiler syntax error, fix ONLY the syntax and preserve semantics. Do not redesign the architecture.
3. If it is a semantic error (e.g., non-traceable participants, broken flow), adjust the diagram to satisfy the feedback. Remove or replace hallucinated components to match the approved plan, but minimize other changes.
4. Do NOT include markdown code fences (like ```plantuml) in your output, just return the raw PlantUML code.
5. You must output exactly the corrected PlantUML file content and absolutely nothing else.
"""

        repaired_diagrams_count = 0
        updated_diagrams_content = dict(diagrams_content)

        for failed_diag in failed_diagrams:
            diag_name = failed_diag.get("diagram", "")
            if diag_name not in diagrams_content:
                continue

            original_puml = diagrams_content[diag_name]
            compiler_stderr = failed_diag.get("stderr", "")
            existing_state = diagram_states.get(diag_name, {})

            user_prompt = f"""The following PlantUML failed validation.

Diagram Name: {diag_name}

Validation Feedback / Compiler Error:
{compiler_stderr}

Original PlantUML:
{original_puml}

Fix the diagram to resolve the feedback. Return ONLY the corrected PlantUML code."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            logger.info("Invoking LLM for repairing %s...", diag_name)
            start_time = time.time()
            llm_response = self.llm.invoke(messages)
            exec_time = int((time.time() - start_time) * 1000)
            
            response_content = llm_response.content
            
            record_agent_cost(
                state.setdefault("metadata", {}), 
                self.name, 
                input_text=system_prompt + user_prompt, 
                output_text=str(response_content),
                latency_ms=exec_time,
                llm_calls=1
            )
            if isinstance(response_content, list):
                response_content = "\n".join([str(item) for item in response_content])
            elif not isinstance(response_content, str):
                response_content = str(response_content)

            clean_content = (
                response_content
                .replace("```plantuml", "")
                .replace("```puml", "")
                .replace("```", "")
                .strip()
            )

            # ------------------------------------------------------------------
            # Task 3 — Duplicate output detection.
            # If the LLM returned the same content it was given, another repair
            # cycle would be pointless.  Immediately mark as VALIDATION_FAILED
            # and do NOT increment repair_attempts (so the accounting stays
            # consistent — the repair produced no useful work).
            # ------------------------------------------------------------------
            previous_output = (existing_state.get("generator_output") or "").strip()
            if clean_content == previous_output:
                failure_reason = "Repair produced identical output — LLM could not fix the syntax error."
                logger.warning(
                    "Duplicate repair output detected — marking VALIDATION_FAILED immediately | "
                    "diagram_id=%s | repair_attempts=%d",
                    diag_name,
                    existing_state.get("repair_attempts", 0),
                )
                diagram_states[diag_name] = {
                    **existing_state,
                    "status": "VALIDATION_FAILED",
                    "failure_reason": failure_reason,
                    "execution_time_ms": existing_state.get("execution_time_ms", 0) + exec_time,
                    # repair_attempts intentionally NOT incremented — no useful work done.
                }
                # Emit into validation report so routing logic sees it.
                # Set retry_requested = False via metadata so the graph continues.
                current_metadata["retry_requested"] = False
                current_metadata["uml_has_permanent_failures"] = True
                logger.info(
                    "retry_requested forced to False — duplicate repair output | diagram_id=%s",
                    diag_name,
                )
                continue

            # ------------------------------------------------------------------
            # Normal path — store repaired content.
            # ------------------------------------------------------------------
            updated_diagrams_content[diag_name] = clean_content
            repaired_diagrams_count += 1
            logger.info("Successfully applied repair patch for %s.", diag_name)

            # Increment repair_attempts so the validator can enforce the ceiling
            # on the next pass.  attempt tracks generation retries separately.
            diagram_states[diag_name] = {
                **existing_state,
                "status": "repaired",
                "generator_output": clean_content,
                "llm_calls": existing_state.get("llm_calls", 0) + 1,
                "execution_time_ms": existing_state.get("execution_time_ms", 0) + exec_time,
                "attempt": existing_state.get("attempt", 0) + 1,
                "repair_attempts": existing_state.get("repair_attempts", 0) + 1,
            }

        logger.info("UML Repair completed %d repair(s).", repaired_diagrams_count)

        new_message = AIMessage(
            content=f"Attempted {repaired_diagrams_count} repair(s).",
            name="uml_repair",
        )

        updated_metadata = {
            **current_metadata,
            "uml_repair_completed": True,
            "last_updated": generate_timestamp(),
        }

        return {
            "plantuml_diagrams": updated_diagrams_content,
            "diagram_execution_states": diagram_states,
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_repair",
        }


# Automatically register the agent
AgentRegistry().register(UMLRepairAgent())
