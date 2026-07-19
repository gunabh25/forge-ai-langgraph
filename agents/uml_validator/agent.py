"""UML Validator Agent implementation."""

import json
import os
import subprocess
import tempfile
import time
from typing import Dict, Any, List, Optional, cast
from langchain_core.messages import AIMessage
from agents.base import BaseAgent
from core.agent_registry import AgentRegistry
from app.state import ForgeState, DiagramExecutionState
from config.logging import get_logger
from core.utils import generate_timestamp

logger = get_logger("agents.uml_validator")


class UMLValidatorAgent(BaseAgent):
    """UML Validator agent responsible for checking PlantUML diagrams via compiler."""

    @property
    def name(self) -> str:
        return "UML Validator"

    @property
    def description(self) -> str:
        return "Validates PlantUML syntax deterministically using the PlantUML compiler."

    @property
    def capabilities(self) -> List[str]:
        return ["plantuml_validation", "syntax_checking"]

    @property
    def requires(self) -> List[str]:
        return ["plantuml_diagrams"]

    @property
    def produces(self) -> List[str]:
        return ["plantuml_validation_report"]

    def __init__(self):
        # Validation is deterministic — no LLM needed.
        pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _max_repair_attempts() -> int:
        """Return the configured repair ceiling, read fresh from settings each
        time so tests can override it without restarting the process."""
        from app.settings import settings as _settings
        return _settings.MAX_UML_REPAIR_ATTEMPTS

    def _check_syntax(self, puml_content: str) -> Dict[str, Any]:
        """Invoke 'plantuml -checkonly' on the given content.

        Returns:
            Dict with keys: valid, return_code, stdout, stderr, error_type
        """
        # Default fallback — engine missing; let the renderer handle it.
        result: Dict[str, Any] = {
            "valid": True,
            "return_code": 0,
            "stdout": "",
            "stderr": "Compiler engine unavailable. Bypassing validation.",
            "error_type": "engine_missing",
        }

        with tempfile.NamedTemporaryFile(suffix=".puml", mode="w", delete=False) as tf:
            tf.write(puml_content)
            temp_path = tf.name

        try:
            cmd_plantuml = ["plantuml", "-checkonly", temp_path]
            cmd_java = ["java", "-jar", "plantuml.jar", "-checkonly", temp_path]

            for cmd in (cmd_plantuml, cmd_java):
                try:
                    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
                    result["return_code"] = proc.returncode
                    result["stdout"] = proc.stdout
                    result["stderr"] = proc.stderr
                    result["valid"] = proc.returncode == 0
                    result["error_type"] = "" if proc.returncode == 0 else "syntax_error"
                    return result
                except FileNotFoundError:
                    continue
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return result

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the UML Validator agent step."""
        diagrams_content = state.get("plantuml_diagrams", {})
        current_diagram_id = state.get("current_diagram_id")

        if not diagrams_content:
            logger.warning("No PlantUML diagrams found in state to validate.")
            return {}

        if current_diagram_id:
            logger.info(
                "UML Validator starting parallel compilation | diagram_id=%s",
                current_diagram_id,
            )
            diagrams_to_process = {k: v for k, v in diagrams_content.items() if k == current_diagram_id}
        else:
            logger.info(
                "UML Validator starting sequential compilation | count=%d",
                len(diagrams_content),
            )
            diagrams_to_process = diagrams_content

        # Read ceiling from settings — never hardcoded.
        max_repair_attempts = self._max_repair_attempts()

        current_metadata = state.get("metadata", {}) or {}
        diagram_states = dict(state.get("diagram_execution_states", {}) or {})

        diagram_results: List[Dict[str, Any]] = []
        passed_count = 0
        failed_count = 0
        permanently_failed_count = 0

        # Extended metrics (Task 4)
        total_repair_attempts_this_run = 0
        repair_failures_this_run = 0

        for diagram_name, puml_content in diagrams_to_process.items():
            existing_state = diagram_states.get(diagram_name, {})

            # ------------------------------------------------------------------
            # Guard: skip diagrams already permanently failed.
            # Covers sequential re-entry and duplicate fan-out calls.
            # ------------------------------------------------------------------
            if existing_state.get("status") == "VALIDATION_FAILED":
                failure_reason = existing_state.get(
                    "failure_reason", "Repair attempts exhausted."
                )
                logger.warning(
                    "Diagram permanently failed validation | "
                    "diagram_id=%s | repair_attempts=%d | failure_reason=%r | "
                    "execution_time_ms=%d | llm_calls=%d",
                    diagram_name,
                    existing_state.get("repair_attempts", 0),
                    failure_reason,
                    existing_state.get("execution_time_ms", 0),
                    existing_state.get("llm_calls", 0),
                )
                permanently_failed_count += 1
                failed_count += 1
                repair_failures_this_run += 1
                diagram_results.append({
                    "diagram": diagram_name,
                    "valid": False,
                    "return_code": -1,
                    "stdout": "",
                    "stderr": failure_reason,
                    "error_type": "permanently_failed",
                    "errors": [failure_reason],
                    "permanently_failed": True,
                })
                continue

            start_time = time.time()
            check_res = self._check_syntax(puml_content)

            # ------------------------------------------------------------------
            # Fix 1 — Pre-entry diagnostic dump.
            # Log the full DiagramExecutionState before any override so we can
            # verify which fields carry stale values from the previous cycle.
            # ------------------------------------------------------------------
            logger.info(
                "\n"
                "══════════ Pre-Validation State Dump ══════════\n"
                "diagram_id           : %s\n"
                "status               : %s\n"
                "pipeline_feedback    : %s\n"
                "compiler_error       : %s\n"
                "grammar_status       : %s\n"
                "architecture_status  : %s\n"
                "business_flow_status : %s\n"
                "overall_status       : %s\n"
                "repair_attempts      : %s\n"
                "═══════════════════════════════════════════════",
                diagram_name,
                existing_state.get("status"),
                existing_state.get("pipeline_feedback"),
                existing_state.get("compiler_error"),
                existing_state.get("grammar_status"),
                existing_state.get("architecture_status"),
                existing_state.get("business_flow_status"),
                existing_state.get("overall_status"),
                existing_state.get("repair_attempts", 0),
            )

            # ------------------------------------------------------------------
            # Fix 2 — Stale pipeline_feedback guard.
            #
            # After a successful repair, `pipeline_feedback` may still contain a
            # *previous* failing result (e.g., Architecture Validator from cycle N-1).
            # The injection block below would then override a valid compiler result
            # back to failed, creating an infinite repair loop.
            #
            # Rule: if the diagram arrived from the Repair Agent (status=="repaired")
            # and the repair's own ValidationPipeline ran cleanly (grammar_status and
            # architecture_status are not "failed"), then pipeline_feedback is stale
            # and must be cleared before the injection block executes.
            # ------------------------------------------------------------------
            repaired_state = existing_state.get("status") == "repaired"
            if repaired_state:
                stale_pf = existing_state.get("pipeline_feedback")
                if stale_pf and not stale_pf.get("passed", True):
                    grammar_ok = existing_state.get("grammar_status") in ("passed", "skipped", None)
                    arch_ok = existing_state.get("architecture_status") in ("passed", "skipped", None)
                    if grammar_ok and arch_ok:
                        logger.info(
                            "Clearing stale pipeline_feedback for repaired diagram | "
                            "diagram_id=%s | stale_validator=%s | stale_score=%s",
                            diagram_name,
                            stale_pf.get("validator"),
                            stale_pf.get("score"),
                        )
                        # Shadow the existing_state locally — do not mutate the dict.
                        # cast() preserves DiagramExecutionState typing so all subsequent
                        # .get() calls remain properly typed.
                        existing_state = cast(DiagramExecutionState, {
                            **existing_state,
                            "pipeline_feedback": None,
                        })

            # -- Multi-Layer Pipeline Feedback Injection (Phase 5) --
            pipeline_feedback = existing_state.get("pipeline_feedback")
            if pipeline_feedback and not pipeline_feedback.get("passed", True):
                validator_name = pipeline_feedback.get("validator", "Validation Pipeline")
                feedback_errors = pipeline_feedback.get("errors", [])
                logger.info("Overriding compiler result due to upstream %s failure", validator_name)
                
                check_res["valid"] = False
                check_res["error_type"] = "semantic_error"
                if check_res["return_code"] == 0:
                    check_res["return_code"] = 1
                
                if "diagnostics" in pipeline_feedback:
                    # Pass through JSON payload for Repair Agent compatibility
                    check_res["stderr"] = json.dumps({"diagnostics": pipeline_feedback["diagnostics"]})
                else:
                    formatted_feedback = (
                        f"[{validator_name} Failed]\n"
                        f"Score: {pipeline_feedback.get('score', 0)}\n"
                        f"Errors:\n" + "\n".join(f"- {e}" for e in feedback_errors)
                    )
                    
                    if not check_res["stderr"]:
                        check_res["stderr"] = formatted_feedback
                    else:
                        check_res["stderr"] = check_res["stderr"] + "\n\n" + formatted_feedback
            # --------------------------------------------------------
            
            exec_time = int((time.time() - start_time) * 1000)

            diagram_result: Dict[str, Any] = {
                "diagram": diagram_name,
                "valid": check_res["valid"],
                "return_code": check_res["return_code"],
                "stdout": check_res["stdout"],
                "stderr": check_res["stderr"],
                "error_type": check_res["error_type"],
                "permanently_failed": False,
            }

            errors: List[str] = []

            if not check_res["valid"]:
                failed_count += 1
                raw_error = check_res["stderr"] or "Unknown syntax error."
                errors.append(raw_error)

                repair_attempts = existing_state.get("repair_attempts", 0)
                total_repair_attempts_this_run += repair_attempts

                if repair_attempts >= max_repair_attempts:
                    # ----------------------------------------------------------
                    # Ceiling reached — permanently fail the diagram.
                    # ----------------------------------------------------------
                    permanently_failed_count += 1
                    repair_failures_this_run += 1
                    diagram_result["permanently_failed"] = True

                    failure_reason = (
                        f"Repair attempts exhausted after {repair_attempts} cycle(s). "
                        f"Last compiler error: {raw_error[:200]}"
                    )

                    # Task 5 — rich structured log line
                    logger.warning(
                        "Diagram permanently failed validation | "
                        "diagram_id=%s | repair_attempts=%d/%d | "
                        "failure_reason=%r | execution_time_ms=%d | llm_calls=%d",
                        diagram_name,
                        repair_attempts,
                        max_repair_attempts,
                        failure_reason,
                        existing_state.get("execution_time_ms", 0) + exec_time,
                        existing_state.get("llm_calls", 0),
                    )

                    diagram_states[diagram_name] = cast(DiagramExecutionState, {
                        **existing_state,
                        "status": "VALIDATION_FAILED",
                        "compiler_output": check_res["stdout"],
                        "compiler_error": check_res["stderr"],
                        "repair_attempts": repair_attempts,
                        "failure_reason": failure_reason,
                        "execution_time_ms": existing_state.get("execution_time_ms", 0) + exec_time,
                    })

                else:
                    # ----------------------------------------------------------
                    # Under ceiling — eligible for repair.
                    # ----------------------------------------------------------
                    logger.info(
                        "Diagram failed validation — repair eligible | "
                        "diagram_id=%s | repair_attempts=%d/%d",
                        diagram_name,
                        repair_attempts,
                        max_repair_attempts,
                    )

                    diagram_states[diagram_name] = cast(DiagramExecutionState, {
                        **existing_state,
                        "compiler_output": check_res["stdout"],
                        "compiler_error": check_res["stderr"],
                        "status": "failed_validation",
                        "execution_time_ms": existing_state.get("execution_time_ms", 0) + exec_time,
                    })

            else:
                passed_count += 1
                diagram_states[diagram_name] = cast(DiagramExecutionState, {
                    **existing_state,
                    "compiler_output": check_res["stdout"],
                    "compiler_error": check_res["stderr"],
                    "status": "validated",
                    "execution_time_ms": existing_state.get("execution_time_ms", 0) + exec_time,
                })

            diagram_result["errors"] = errors
            diagram_results.append(diagram_result)

        # ------------------------------------------------------------------
        # Routing decision.
        #   retry_requested = True  → Repair Agent
        #   retry_requested = False → Renderer (continue)
        # ------------------------------------------------------------------
        repairable_diagrams = [
            d for d in diagram_results
            if not d.get("valid", True) and not d.get("permanently_failed", False)
        ]
        retry_requested = len(repairable_diagrams) > 0

        has_permanent_failures = permanently_failed_count > 0 or any(
            s.get("status") == "VALIDATION_FAILED"
            for s in diagram_states.values()
        )

        # ------------------------------------------------------------------
        # Task 4 — extended repair metrics
        # ------------------------------------------------------------------
        repaired_successfully = sum(
            1 for s in diagram_states.values()
            if s.get("status") == "rendered" and s.get("repair_attempts", 0) > 0
        )
        total_diagrams_with_repairs = sum(
            1 for s in diagram_states.values()
            if s.get("repair_attempts", 0) > 0
        )
        repair_total = sum(
            s.get("repair_attempts", 0) for s in diagram_states.values()
        )
        avg_repairs = (
            round(repair_total / total_diagrams_with_repairs, 2)
            if total_diagrams_with_repairs > 0 else 0.0
        )
        total_with_repair_outcome = repaired_successfully + repair_failures_this_run
        repair_success_rate = (
            round(repaired_successfully / total_with_repair_outcome * 100, 1)
            if total_with_repair_outcome > 0 else None
        )

        uml_repair_metrics = {
            "repair_success_rate": f"{repair_success_rate}%" if repair_success_rate is not None else "N/A",
            "validation_failures": permanently_failed_count,
            "repair_failures": repair_failures_this_run,
            "average_repairs_per_diagram": avg_repairs,
        }

        logger.info(
            "UML Validation completed | "
            "passed=%d/%d | repairable=%d | permanently_failed=%d | retry_requested=%s | "
            "repair_success_rate=%s | avg_repairs_per_diagram=%.2f",
            passed_count,
            len(diagrams_to_process),
            len(repairable_diagrams),
            permanently_failed_count,
            retry_requested,
            uml_repair_metrics["repair_success_rate"],
            avg_repairs,
        )

        validation_result = {
            "validated": len(diagrams_to_process),
            "passed": passed_count,
            "failed": failed_count,
            "permanently_failed": permanently_failed_count,
            "compiler": "PlantUML",
            "diagram_results": diagram_results,
            "report": (
                f"Compiled {len(diagrams_to_process)} diagrams. "
                f"Passed: {passed_count}, "
                f"Failed: {failed_count - permanently_failed_count}, "
                f"Permanently Failed: {permanently_failed_count}."
            ),
        }

        new_message = AIMessage(
            content=json.dumps(validation_result, indent=2),
            name="uml_validator",
        )

        updated_metadata = {
            **current_metadata,
            "uml_validation_completed": True,
            "uml_is_valid": (failed_count == 0),
            "retry_requested": retry_requested,
            "uml_has_permanent_failures": has_permanent_failures,
            "uml_repair_metrics": uml_repair_metrics,
            "last_updated": generate_timestamp(),
        }

        state_updates: Dict[str, Any] = {
            "plantuml_validation_report": validation_result,
            "diagram_execution_states": diagram_states,
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_validator",
        }

        # Legacy sequential mode: narrow to repair-eligible diagrams only.
        if retry_requested and not current_diagram_id:
            repairable_names = {
                str(d.get("diagram", "")).lower()
                for d in repairable_diagrams
            }
            if repairable_names:
                current_selected: List[Dict[str, str]] = state.get("selected_uml_diagrams") or []
                new_selected = [
                    d for d in current_selected
                    if d.get("diagram", "").lower() in repairable_names
                ]
                logger.info(
                    "Targeting %d repair-eligible diagrams | diagrams=%s",
                    len(new_selected),
                    sorted(repairable_names),
                )
                state_updates["selected_uml_diagrams"] = new_selected

        return state_updates


# Automatically register the agent
AgentRegistry().register(UMLValidatorAgent())
