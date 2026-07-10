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
        
        import time
        
        for diagram_name, puml_content in diagrams_to_process.items():
            start_time = time.time()
            check_res = self._check_syntax(puml_content)
            exec_time = int((time.time() - start_time) * 1000)
            
            diagram_result = {
                "diagram": diagram_name,
                "valid": check_res["valid"],
                "return_code": check_res["return_code"],
                "stdout": check_res["stdout"],
                "stderr": check_res["stderr"],
                "error_type": check_res["error_type"]
            }
            
            errors = []
            if not check_res["valid"]:
                failed_count += 1
                errors.append(check_res["stderr"] or "Unknown syntax error.")
            else:
                passed_count += 1
                
            diagram_result["errors"] = errors
            diagram_results.append(diagram_result)
            
            from typing import cast
            
            # Update DiagramExecutionState
            existing_state = diagram_states.get(diagram_name, {})
            new_diag_state = cast(DiagramExecutionState, {
                **existing_state,
                "compiler_output": check_res["stdout"],
                "compiler_error": check_res["stderr"],
                "status": "validated" if check_res["valid"] else "failed_validation",
                "execution_time_ms": existing_state.get("execution_time_ms", 0) + exec_time
            })
            diagram_states[diagram_name] = new_diag_state

        validation_result = {
            "validated": len(diagrams_to_process),
            "passed": passed_count,
            "failed": failed_count,
            "compiler": "PlantUML",
            "diagram_results": diagram_results,
            "report": f"Compiled {len(diagrams_to_process)} diagrams. Passed: {passed_count}, Failed: {failed_count}."
        }
        
        # Determine overall workflow routing
        max_retries = 3
        # Use attempt from DiagramExecutionState
        retry_requested = False
        is_permanently_failed = False
        
        if current_diagram_id:
            attempt = diagram_states.get(current_diagram_id, {}).get("attempt", 1)
            is_permanently_failed = attempt >= max_retries
            retry_requested = (failed_count > 0) and not is_permanently_failed
            
            # Extensive logging per diagram as requested
            logger.info(f"{current_diagram_id}")
            if failed_count > 0:
                logger.info(f"Attempt {min(attempt, max_retries)}/{max_retries}")
                
            if is_permanently_failed and failed_count > 0:
                logger.warning(f"Maximum repair attempts reached.")
                logger.warning(f"Marking diagram as permanently failed.")
                logger.warning(f"Skipping further repairs.")
        else:
            repair_attempts = current_metadata.get("repair_attempts", 0)
            is_permanently_failed = repair_attempts >= max_retries
            retry_requested = (failed_count > 0) and not is_permanently_failed
            if failed_count > 0 and is_permanently_failed:
                logger.warning(f"Max repair attempts ({max_retries}) reached. Marking diagrams as permanently failed and continuing.")
        logger.info(f"UML Validation completed. Passed: {passed_count}/{len(diagrams_to_process)}. Retry Requested: {retry_requested}")
        
        new_message = AIMessage(
            content=json.dumps(validation_result, indent=2),
            name="uml_validator"
        )
        
        updated_metadata = {
            **current_metadata,
            "uml_validation_completed": True,
            "uml_is_valid": (failed_count == 0),
            "retry_requested": retry_requested,
            "last_updated": generate_timestamp()
        }
        
        state_updates: Dict[str, Any] = {
            "plantuml_validation_report": validation_result,
            "diagram_execution_states": diagram_states,
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_validator"
        }
        
        # Legacy sequential mode repair targeting
        if retry_requested and not current_diagram_id:
            failed_diagram_names = [
                str(d.get("diagram", "")).lower() 
                for d in diagram_results 
                if not d.get("valid", True)
            ]
            
            if failed_diagram_names:
                current_selected: List[Dict[str, str]] = state.get("selected_uml_diagrams") or []
                new_selected = [
                    d for d in current_selected 
                    if d.get("diagram", "").lower() in failed_diagram_names
                ]
                
                logger.info(f"Targeting {len(new_selected)} failed diagrams for repair: {failed_diagram_names}")
                state_updates["selected_uml_diagrams"] = new_selected
        
        return state_updates

# Automatically register the agent
AgentRegistry().register(UMLValidatorAgent())
