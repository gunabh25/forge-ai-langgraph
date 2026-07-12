"""UML Validator Agent implementation."""

import json
import os
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage
from agents.base import BaseAgent
from core.agent_registry import AgentRegistry
from app.state import ForgeState, DiagramExecutionState
from config.logging import get_logger
from core.utils import generate_timestamp

logger = get_logger("agents.uml_validator")

# ---------------------------------------------------------------------------
# Hard ceiling for repair cycles per diagram.
# After MAX_REPAIR_ATTEMPTS the diagram is permanently marked VALIDATION_FAILED
# and the workflow continues with all remaining successful diagrams.
# ---------------------------------------------------------------------------
MAX_REPAIR_ATTEMPTS = 2


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
        # We no longer instantiate or need self._llm since validation is deterministic
        pass

    def _check_syntax(self, puml_content: str) -> Dict[str, Any]:
        """Invoke 'plantuml -checkonly' on the given content.
        
        Returns:
            Dict containing valid, return_code, stdout, stderr, error_type
        """
        # Default fallback in case engine is entirely missing
        result = {
            "valid": True,  # If engine is missing, pass it to renderer to handle missing engine
            "return_code": 0,
            "stdout": "",
            "stderr": "Compiler engine unavailable. Bypassing validation.",
            "error_type": "engine_missing"
        }
        
        with tempfile.NamedTemporaryFile(suffix=".puml", mode="w", delete=False) as tf:
            tf.write(puml_content)
            temp_path = tf.name

        try:
            cmd_plantuml = ["plantuml", "-checkonly", temp_path]
            cmd_java = ["java", "-jar", "plantuml.jar", "-checkonly", temp_path]
            
            # Try plantuml binary
            try:
                proc = subprocess.run(cmd_plantuml, check=False, capture_output=True, text=True)
                result["return_code"] = proc.returncode
                result["stdout"] = proc.stdout
                result["stderr"] = proc.stderr
                result["valid"] = (proc.returncode == 0)
                result["error_type"] = "" if proc.returncode == 0 else "syntax_error"
                return result
            except FileNotFoundError:
                pass
                
            # Try java -jar plantuml.jar
            try:
                proc = subprocess.run(cmd_java, check=False, capture_output=True, text=True)
                result["return_code"] = proc.returncode
                result["stdout"] = proc.stdout
                result["stderr"] = proc.stderr
                result["valid"] = (proc.returncode == 0)
                result["error_type"] = "" if proc.returncode == 0 else "syntax_error"
                return result
            except FileNotFoundError:
                pass
                
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        return result

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the UML Validator agent step."""
        diagrams_content = state.get("plantuml_diagrams", {})
        current_diagram_id = state.get("current_diagram_id")
        
        if not diagrams_content:
            logger.warning("No PlantUML diagrams found in state to validate.")
            return {}
            
        if current_diagram_id:
            logger.info(f"UML Validator starting parallel compilation for diagram: {current_diagram_id}")
            diagrams_to_process = {k: v for k, v in diagrams_content.items() if k == current_diagram_id}
        else:
            logger.info(f"UML Validator starting sequential compiler execution for {len(diagrams_content)} diagrams...")
            diagrams_to_process = diagrams_content
        
        current_metadata = state.get("metadata", {}) or {}
        diagram_states = dict(state.get("diagram_execution_states", {}) or {})
        
        diagram_results = []
        passed_count = 0
        failed_count = 0
        permanently_failed_count = 0
        
        import time
        
        for diagram_name, puml_content in diagrams_to_process.items():
            existing_state = diagram_states.get(diagram_name, {})

            # ------------------------------------------------------------------
            # Guard: never re-validate a diagram already permanently failed.
            # This can happen in sequential mode if the validator is re-entered.
            # ------------------------------------------------------------------
            if existing_state.get("status") == "VALIDATION_FAILED":
                logger.warning(
                    "Skipping validation — diagram already permanently failed | "
                    "diagram_id=%s | repair_attempts=%d | final_status=VALIDATION_FAILED",
                    diagram_name,
                    existing_state.get("repair_attempts", 0),
                )
                permanently_failed_count += 1
                failed_count += 1
                diagram_results.append({
                    "diagram": diagram_name,
                    "valid": False,
                    "return_code": -1,
                    "stdout": "",
                    "stderr": "Diagram permanently failed validation — repair attempts exhausted.",
                    "error_type": "permanently_failed",
                    "errors": ["Repair attempts exhausted. Diagram marked VALIDATION_FAILED."],
                    "permanently_failed": True,
                })
                continue

            start_time = time.time()
            check_res = self._check_syntax(puml_content)
            exec_time = int((time.time() - start_time) * 1000)
            
            diagram_result = {
                "diagram": diagram_name,
                "valid": check_res["valid"],
                "return_code": check_res["return_code"],
                "stdout": check_res["stdout"],
                "stderr": check_res["stderr"],
                "error_type": check_res["error_type"],
                "permanently_failed": False,
            }
            
            errors = []
            if not check_res["valid"]:
                failed_count += 1
                errors.append(check_res["stderr"] or "Unknown syntax error.")

                # Read per-diagram repair_attempts from DiagramExecutionState.
                # This is reliable in both sequential and parallel (fan-out) modes
                # because each diagram branch carries its own state slice.
                repair_attempts = existing_state.get("repair_attempts", 0)

                if repair_attempts >= MAX_REPAIR_ATTEMPTS:
                    # --------------------------------------------------------
                    # Permanently fail this diagram — ceiling reached.
                    # --------------------------------------------------------
                    permanently_failed_count += 1
                    diagram_result["permanently_failed"] = True

                    logger.warning(
                        "Diagram permanently failed validation | "
                        "diagram_id=%s | repair_attempts=%d/%d | final_status=VALIDATION_FAILED",
                        diagram_name,
                        repair_attempts,
                        MAX_REPAIR_ATTEMPTS,
                    )

                    from typing import cast
                    diagram_states[diagram_name] = cast(DiagramExecutionState, {
                        **existing_state,
                        "status": "VALIDATION_FAILED",
                        "compiler_output": check_res["stdout"],
                        "compiler_error": check_res["stderr"],
                        "repair_attempts": repair_attempts,
                        "execution_time_ms": existing_state.get("execution_time_ms", 0) + exec_time,
                    })
                else:
                    # --------------------------------------------------------
                    # Under the ceiling — standard failed_validation status.
                    # --------------------------------------------------------
                    from typing import cast
                    diagram_states[diagram_name] = cast(DiagramExecutionState, {
                        **existing_state,
                        "compiler_output": check_res["stdout"],
                        "compiler_error": check_res["stderr"],
                        "status": "failed_validation",
                        "execution_time_ms": existing_state.get("execution_time_ms", 0) + exec_time,
                    })

                    logger.info(
                        "Diagram failed validation — repair eligible | "
                        "diagram_id=%s | repair_attempts=%d/%d",
                        diagram_name,
                        repair_attempts,
                        MAX_REPAIR_ATTEMPTS,
                    )
            else:
                passed_count += 1
                from typing import cast
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
        # Determine routing outcome.
        #
        # retry_requested = True  →  route to UML Repair Agent
        # retry_requested = False →  route to Renderer (continue)
        #
        # A diagram is repair-eligible only when:
        #   - it failed validation, AND
        #   - it has NOT yet hit the MAX_REPAIR_ATTEMPTS ceiling.
        # ------------------------------------------------------------------
        repairable_diagrams = [
            d for d in diagram_results
            if not d.get("valid", True) and not d.get("permanently_failed", False)
        ]
        retry_requested = len(repairable_diagrams) > 0

        # Detect whether any diagram has been permanently failed in this or
        # any prior validator invocation (covers sequential multi-pass).
        has_permanent_failures = permanently_failed_count > 0 or any(
            s.get("status") == "VALIDATION_FAILED"
            for s in diagram_states.values()
        )

        logger.info(
            "UML Validation completed | "
            "passed=%d/%d | failed=%d | permanently_failed=%d | retry_requested=%s",
            passed_count,
            len(diagrams_to_process),
            failed_count - permanently_failed_count,
            permanently_failed_count,
            retry_requested,
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
                f"Passed: {passed_count}, Failed: {failed_count - permanently_failed_count}, "
                f"Permanently Failed: {permanently_failed_count}."
            ),
        }
        
        new_message = AIMessage(
            content=json.dumps(validation_result, indent=2),
            name="uml_validator"
        )
        
        updated_metadata = {
            **current_metadata,
            "uml_validation_completed": True,
            "uml_is_valid": (failed_count == 0),
            "retry_requested": retry_requested,
            "uml_has_permanent_failures": has_permanent_failures,
            "last_updated": generate_timestamp(),
        }
        
        state_updates: Dict[str, Any] = {
            "plantuml_validation_report": validation_result,
            "diagram_execution_states": diagram_states,
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_validator",
        }
        
        # Legacy sequential mode: narrow selected_uml_diagrams to only those
        # diagrams that are repair-eligible (failed but not permanently failed).
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
                    list(repairable_names),
                )
                state_updates["selected_uml_diagrams"] = new_selected
        
        return state_updates


# Automatically register the agent
AgentRegistry().register(UMLValidatorAgent())
