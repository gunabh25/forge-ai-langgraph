"""UML Repair Agent implementation — Phase 7.2 Traceability Synchronization.

The Repair Agent is a *constrained editor*, not a designer.
It may ONLY perform these six localized edits:
  1. Rename participant (to an approved name)
  2. Modify a message label
  3. Modify a relationship arrow type
  4. Remove an illegal participant
  5. Add a missing edge between existing participants
  6. Remove a duplicate edge

It MUST NOT invent new participants, services, or architectural layers.
All repairs are constrained against the same Planning JSON that the Generator used.
Illegal participants are rejected before ValidationPipeline is ever called.
"""

import json
import time
from typing import Dict, Any, List, Optional, Tuple

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from agents.base import BaseAgent
from core.llm import get_llm
from core.agent_registry import AgentRegistry
from app.state import ForgeState
from config.logging import get_logger
from core.utils import generate_timestamp
from core.cost_tracker import record_agent_cost
from core.business_normalizer import normalize_name

logger = get_logger("agents.uml_repair")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_allowed_participants(diagram_plan: str) -> Dict[str, str]:
    """Parse the Planning JSON and return {normalized_name: original_name} for
    every approved participant across all four participant categories.

    Returns an empty dict if parsing fails (fail-open — traceability gate will
    skip enforcement rather than block all repairs when plan is absent).
    """
    if not diagram_plan:
        return {}
    try:
        plan_data = json.loads(diagram_plan)
    except (json.JSONDecodeError, TypeError):
        logger.warning("diagram_plan is not valid JSON — traceability gate will be skipped.")
        return {}

    allowed: Dict[str, str] = {}
    for key in ("actors", "external_systems", "major_components", "major_data_stores"):
        for item in plan_data.get(key, []):
            if isinstance(item, str):
                allowed[normalize_name(item)] = item
            elif isinstance(item, dict) and "name" in item:
                allowed[normalize_name(item["name"])] = item["name"]
    return allowed


def _format_allowed_participants_block(allowed: Dict[str, str]) -> str:
    """Return a readable bullet list of approved participant names."""
    if not allowed:
        return "  (No planning JSON available — use only participants already in the diagram.)"
    names = sorted(allowed.values())
    return "\n".join(f"  - {n}" for n in names)


def _build_structured_feedback(compiler_stderr: str, allowed: Dict[str, str]) -> str:
    """Convert raw compiler/validation stderr into structured, actionable feedback.

    For generic syntax errors the raw text is kept.
    For Architecture Validator traceability failures a structured block is produced.
    """
    if not compiler_stderr:
        return "(No specific validation feedback available.)"

    lower = compiler_stderr.lower()
    allowed_block = _format_allowed_participants_block(allowed)

    # Detect an Architecture / traceability failure from ArchitectureValidator
    if "non-traceable" in lower or "invented" in lower or "traceability" in lower:
        return (
            "Validation Layer  : Architecture\n"
            "Rule Violated     : Traceability\n"
            f"Raw Feedback      : {compiler_stderr.strip()}\n\n"
            "Approved Participants (the ONLY names you may use):\n"
            f"{allowed_block}\n\n"
            "Required Fix: Remove every participant that is NOT in the approved list above.\n"
            "Do NOT add any new participant to compensate. Reuse the existing approved ones."
        )

    # Detect relationship / graph errors
    if "graph error" in lower or "dangling" in lower or "duplicate" in lower or "self-loop" in lower:
        return (
            "Validation Layer  : Architecture\n"
            "Rule Violated     : Relationship Integrity\n"
            f"Raw Feedback      : {compiler_stderr.strip()}\n\n"
            "Required Fix: Fix only the relationship issue described above.\n"
            "Do NOT add or rename participants."
        )

    # Default: pass through for syntax errors
    return compiler_stderr.strip()


def _check_traceability(
    plantuml_content: str,
    allowed: Dict[str, str],
) -> List[str]:
    """Parse plantuml_content and return a list of illegal participant display
    names — those whose normalized name is not in allowed.

    Returns an empty list when allowed is empty (fail-open when no plan).
    """
    if not allowed:
        return []

    from agents.uml_generator.uml_parser import PlantUMLParser
    try:
        diagram = PlantUMLParser.parse(plantuml_content)
    except Exception as exc:
        logger.warning("Traceability gate: parser raised %s — skipping enforcement.", exc)
        return []

    illegal: List[str] = []
    for node in diagram.business_nodes:
        norm = node.normalized_name
        if norm not in allowed:
            # Allow trivial subset overlap (same logic as Generator)
            match = next(
                (a for a in allowed if norm in a or a in norm),
                None,
            )
            if not match:
                illegal.append(node.display_name)

    return illegal


def _apply_lexical_fix(
    plantuml_content: str,
    allowed: Dict[str, str],
) -> Tuple[str, bool, List[str]]:
    """Apply deterministic lexical renaming for subset-matched participants.

    Mutates UMLNode.display_name and serializes with diagram.to_plantuml().
    Returns (fixed_content, any_fixes_applied, list_of_fix_descriptions).

    This mirrors the identical logic in UMLGeneratorAgent (generator traceability block).
    No LLM is invoked — this is fully deterministic.
    """
    if not allowed:
        return plantuml_content, False, []

    from agents.uml_generator.uml_parser import PlantUMLParser
    try:
        diagram = PlantUMLParser.parse(plantuml_content)
    except Exception as exc:
        logger.warning("Lexical fix: parser raised %s — skipping.", exc)
        return plantuml_content, False, []

    fixes: List[str] = []
    for node in diagram.business_nodes:
        norm = node.normalized_name
        if norm not in allowed:
            match = next(
                (a for a in allowed if norm in a or a in norm),
                None,
            )
            if match:
                original_display = node.display_name
                node.display_name = allowed[match]
                node.alias = node.display_name
                fixes.append(f"{original_display!r} -> {node.display_name!r}")

    if fixes:
        return diagram.to_plantuml(), True, fixes
    return plantuml_content, False, []


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class UMLRepairAgent(BaseAgent):
    """UML Repair Agent — constrained editor with traceability synchronization.

    Enforces the same deterministic traceability guarantees as the Generator:
    - Receives the same Planning JSON as an immutable constraint.
    - Rejects repaired output containing illegal participants *before* validation.
    - Applies deterministic lexical fixes instead of LLM calls for trivial renames.
    """

    @property
    def name(self) -> str:
        return "UML Repair Agent"

    @property
    def description(self) -> str:
        return "Repairs PlantUML diagrams using only approved architectural participants."

    @property
    def capabilities(self) -> List[str]:
        return ["plantuml_repair", "syntax_correction", "traceability_enforcement"]

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
        """Execute the UML Repair Agent step with traceability enforcement."""
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

        # Exclude permanently-failed diagrams.
        failed_diagrams = [
            d for d in failed_diagrams
            if not d.get("permanently_failed", False)
            and diagram_states.get(d.get("diagram", ""), {}).get("status") != "VALIDATION_FAILED"
        ]

        if not failed_diagrams:
            logger.info("No repair-eligible diagrams found. Exiting repair agent.")
            return {}

        logger.info("UML Repair starting execution for %d failed diagram(s)...", len(failed_diagrams))

        repaired_diagrams_count = 0
        updated_diagrams_content = dict(diagrams_content)

        for failed_diag in failed_diagrams:
            diag_name = failed_diag.get("diagram", "")
            if diag_name not in diagrams_content:
                continue

            original_puml = diagrams_content[diag_name]
            compiler_stderr = failed_diag.get("stderr", "")
            existing_state = diagram_states.get(diag_name, {})
            repair_attempt_number = existing_state.get("repair_attempts", 0) + 1

            # ── Task 1: Extract approved Planning JSON ─────────────────────
            diagram_type = existing_state.get("diagram_type") or ""
            diagram_plan = existing_state.get("diagram_plan") or ""
            allowed = _extract_allowed_participants(diagram_plan)
            allowed_block = _format_allowed_participants_block(allowed)

            # ── Task 4: Structured validation feedback ─────────────────────
            structured_feedback = _build_structured_feedback(compiler_stderr, allowed)

            # ── Task 8: Logging — repair attempt header ────────────────────
            logger.info(
                "\n============================== Repair Attempt %d ==============================\n"
                "Diagram     : %s\n"
                "Diagram Type: %s\n"
                "Feedback    :\n%s\n"
                "Approved    : %s\n"
                "===============================================================================",
                repair_attempt_number,
                diag_name,
                diagram_type,
                structured_feedback,
                list(allowed.values()) if allowed else "(none — plan unavailable)",
            )

            # ── Tasks 2 & 3: Constrained system prompt ─────────────────────
            system_prompt = (
                "You are a highly specialized UML Repair Agent operating as a CONSTRAINED EDITOR.\n\n"
                "## YOUR ONLY JOB\n"
                "Fix the specific validation errors in the PlantUML diagram provided.\n"
                "You are NOT allowed to redesign, reorder, or reimagine the diagram.\n\n"
                "## APPROVED PARTICIPANTS — IMMUTABLE CONSTRAINT\n"
                "The following participants were approved during architectural planning.\n"
                "You MUST use ONLY these names as participants:\n\n"
                f"{allowed_block}\n\n"
                "## YOU MUST NOT:\n"
                "- Invent new participants\n"
                "- Invent new services or systems\n"
                "- Invent new business capabilities\n"
                "- Invent orchestration layers, schedulers, managers, repositories, or backend services\n"
                "- Add any participant not in the APPROVED PARTICIPANTS list above\n"
                "- Redesign the architecture\n"
                "- Reorder the entire flow\n"
                "- Replace business capabilities\n\n"
                "## ALLOWED EDITS (choose the minimal set needed to fix the error):\n"
                "1. Rename a participant — ONLY to an approved name from the list above\n"
                "2. Modify a message label\n"
                "3. Modify a relationship arrow type\n"
                "4. Remove an illegal participant (one not in the approved list)\n"
                "5. Add a missing edge between existing approved participants\n"
                "6. Remove a duplicate edge\n\n"
                "## OUTPUT FORMAT\n"
                "Return ONLY the corrected PlantUML code.\n"
                "Do NOT include markdown fences (``` or ```plantuml).\n"
                "Do NOT add any explanation or commentary.\n\n"
                f"## REPAIR FOCUS (Attempt {repair_attempt_number})\n"
            )

            if repair_attempt_number == 1:
                system_prompt += (
                    "Fix ONLY the specific errors listed in the validation feedback. "
                    "Do not touch anything else."
                )
            else:
                system_prompt += (
                    "Fix ONLY the remaining validation errors. "
                    "Be progressively narrower. Never regenerate the full sequence."
                )

            # ── Task 7: Repair budget narrowing in user prompt ─────────────
            user_prompt = (
                f"Diagram Name: {diag_name}\n"
                f"Repair Attempt: {repair_attempt_number}\n\n"
                f"Validation Feedback:\n{structured_feedback}\n\n"
                f"Original PlantUML:\n{original_puml}\n\n"
                "Fix the diagram to resolve the feedback using ONLY approved participants.\n"
                "Return ONLY the corrected PlantUML code."
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            logger.info("Invoking LLM for repair | diagram_id=%s | attempt=%d", diag_name, repair_attempt_number)
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
                llm_calls=1,
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
            # Duplicate-output detection
            # ------------------------------------------------------------------
            previous_output = (existing_state.get("generator_output") or "").strip()
            if clean_content == previous_output:
                failure_reason = "Repair produced identical output — LLM could not fix the validation error."
                logger.warning(
                    "Duplicate repair output detected — marking VALIDATION_FAILED | "
                    "diagram_id=%s | repair_attempt=%d",
                    diag_name,
                    repair_attempt_number,
                )
                diagram_states[diag_name] = {
                    **existing_state,
                    "status": "VALIDATION_FAILED",
                    "failure_reason": failure_reason,
                    "execution_time_ms": existing_state.get("execution_time_ms", 0) + exec_time,
                }
                current_metadata["retry_requested"] = False
                current_metadata["uml_has_permanent_failures"] = True
                continue

            # ── Task 6: Deterministic lexical fix ─────────────────────────
            clean_content, lexical_applied, lexical_fixes = _apply_lexical_fix(clean_content, allowed)
            if lexical_applied:
                logger.info(
                    "Lexical fix applied | diagram_id=%s | renames=%s",
                    diag_name,
                    lexical_fixes,
                )

            # ── Tasks 4 & 5: Post-repair traceability gate ─────────────────
            illegal_participants = _check_traceability(clean_content, allowed)

            if illegal_participants:
                # ── Task 8: Traceability gate rejection log ────────────────
                logger.warning(
                    "\n"
                    "────────────────── Traceability Gate: REJECTED ──────────────────\n"
                    "Diagram       : %s\n"
                    "Attempt       : %d\n"
                    "Illegal       : %s\n"
                    "Action        : Repair rejected BEFORE ValidationPipeline.\n"
                    "─────────────────────────────────────────────────────────────────",
                    diag_name,
                    repair_attempt_number,
                    illegal_participants,
                )

                # Build structured gate feedback for the NEXT repair attempt
                gate_feedback = (
                    f"Validation Layer  : Traceability Gate (Pre-Validation)\n"
                    f"Illegal Participants Detected: {', '.join(illegal_participants)}\n\n"
                    f"Approved Participants:\n{allowed_block}\n\n"
                    f"Required Fix: Remove ONLY the illegal participant(s) listed above. "
                    f"Do NOT introduce any replacement participant. "
                    f"Reuse an existing approved participant instead."
                )

                # Update diagram_results so the next repair cycle gets structured gate feedback
                for dr in diagram_results:
                    if dr.get("diagram") == diag_name:
                        dr["stderr"] = gate_feedback
                        dr["valid"] = False
                        break

                diagram_states[diag_name] = {
                    **existing_state,
                    "status": "repaired",           # allow another repair cycle
                    "generator_output": original_puml,  # keep original — gate rejected repair
                    "llm_calls": existing_state.get("llm_calls", 0) + 1,
                    "execution_time_ms": existing_state.get("execution_time_ms", 0) + exec_time,
                    "attempt": existing_state.get("attempt", 0) + 1,
                    "repair_attempts": repair_attempt_number,
                    "pipeline_feedback": {
                        "validator": "Traceability Gate",
                        "passed": False,
                        "score": 0,
                        "errors": [f"Illegal participants detected: {', '.join(illegal_participants)}"],
                        "warnings": [],
                    },
                    "grammar_status": existing_state.get("grammar_status", "skipped"),
                    "architecture_status": "failed",
                    "business_flow_status": "skipped",
                }
                repaired_diagrams_count += 1
                continue

            # ── Task 8: Traceability gate pass log ─────────────────────────
            logger.info(
                "Traceability Gate: PASS | diagram_id=%s | attempt=%d | all participants approved",
                diag_name,
                repair_attempt_number,
            )

            # ------------------------------------------------------------------
            # Semantic validation (ValidationPipeline) — only reached when the
            # traceability gate passes. ArchitectureValidator never sees invented
            # participants.
            # ------------------------------------------------------------------
            from agents.uml_generator.validators import ValidationPipeline
            pipeline = ValidationPipeline(self.llm)

            val_res = pipeline.validate_diagram(diagram_type, diagram_plan, clean_content)
            clean_content = val_res.get("fixed_content", clean_content)
            pipeline_feedback = val_res.get("pipeline_feedback")
            uml_validation_metrics = val_res.get("uml_validation_metrics", {})
            syntax_valid = val_res.get("syntax_valid", False)
            grammar_status = val_res.get("grammar_status", "failed")
            architecture_status = val_res.get("architecture_status", "skipped")
            business_flow_status = val_res.get("business_flow_status", "skipped")

            # ── Task 8: Final outcome log ──────────────────────────────────
            logger.info(
                "\n"
                "────────────────── Repair Outcome ──────────────────\n"
                "Diagram         : %s\n"
                "Attempt         : %d\n"
                "Illegal Ptcps   : None\n"
                "Architecture    : %s\n"
                "Business Flow   : %s\n"
                "Syntax Valid    : %s\n"
                "─────────────────────────────────────────────────────",
                diag_name,
                repair_attempt_number,
                architecture_status.upper(),
                business_flow_status.upper(),
                syntax_valid,
            )

            updated_diagrams_content[diag_name] = clean_content
            repaired_diagrams_count += 1
            logger.info("Successfully applied repair patch | diagram_id=%s", diag_name)

            diagram_states[diag_name] = {
                **existing_state,
                "status": "repaired",
                "generator_output": clean_content,
                # Clear stale compiler artefacts from the previous failed cycle
                # so UMLValidatorAgent does not re-read an obsolete error on the
                # next validation pass.
                "compiler_error": None,
                "compiler_output": "",
                "llm_calls": existing_state.get("llm_calls", 0) + 1,
                "execution_time_ms": existing_state.get("execution_time_ms", 0) + exec_time,
                "attempt": existing_state.get("attempt", 0) + 1,
                "repair_attempts": repair_attempt_number,
                "pipeline_feedback": pipeline_feedback,
                "uml_validation_metrics": uml_validation_metrics,
                "grammar_status": grammar_status,
                "architecture_status": architecture_status,
                "business_flow_status": business_flow_status,
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
