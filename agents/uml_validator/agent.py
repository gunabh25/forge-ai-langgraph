"""UML Validator Agent implementation."""

import json
import os
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage
from agents.base import BaseAgent
from core.agent_registry import AgentRegistry
from app.state import ForgeState
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
        
        if not diagrams_content:
            logger.warning("No PlantUML diagrams found in state to validate.")
            return {}
            
        logger.info(f"UML Validator starting compiler execution for {len(diagrams_content)} diagrams...")
        
        current_metadata = state.get("metadata", {}) or {}
        repair_attempts = current_metadata.get("repair_attempts", 0)
        
        diagram_results = []
        passed_count = 0
        failed_count = 0
        
        # Only validate the ones that haven't been successfully validated yet? 
        # For simplicity, we can validate all or rely on 'selected_uml_diagrams' for tracking active failures.
        # But compiling is fast, so we compile all.
        
        for diagram_name, puml_content in diagrams_content.items():
            check_res = self._check_syntax(puml_content)
            
            diagram_result = {
                "diagram": diagram_name,
                "valid": check_res["valid"],
                "return_code": check_res["return_code"],
                "stdout": check_res["stdout"],
                "stderr": check_res["stderr"],
                "error_type": check_res["error_type"]
            }
            
            # Additional detail for the report
            errors = []
            if not check_res["valid"]:
                failed_count += 1
                errors.append(check_res["stderr"] or "Unknown syntax error.")
            else:
                passed_count += 1
                
            diagram_result["errors"] = errors
            diagram_results.append(diagram_result)

        validation_result = {
            "validated": len(diagrams_content),
            "passed": passed_count,
            "failed": failed_count,
            "repair_attempts": repair_attempts,
            "compiler": "PlantUML",
            "diagram_results": diagram_results,
            "report": f"Compiled {len(diagrams_content)} diagrams. Passed: {passed_count}, Failed: {failed_count}."
        }
        
        # Determine overall workflow routing
        max_retries = 3
        is_permanently_failed = repair_attempts >= max_retries
        
        # We request a retry if there are failed diagrams AND we haven't hit the limit.
        retry_requested = (failed_count > 0) and not is_permanently_failed
        
        if failed_count > 0 and is_permanently_failed:
            logger.warning(f"Max repair attempts ({max_retries}) reached. Marking diagrams as permanently failed and continuing.")
            
        logger.info(f"UML Validation completed. Passed: {passed_count}/{len(diagrams_content)}. Retry Requested: {retry_requested}")
        
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
        
        state_updates = {
            "plantuml_validation_report": validation_result,
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_validator"
        }
        
        # If we are retrying, set up the targeted list so the Repair Agent knows what to fix
        if retry_requested:
            failed_diagram_names = [
                str(d.get("diagram", "")).lower() 
                for d in diagram_results 
                if not d.get("valid", True)
            ]
            
            if failed_diagram_names:
                current_selected: List[Dict[str, Any]] = state.get("selected_uml_diagrams") or []
                new_selected = [
                    d for d in current_selected 
                    if str(d.get("diagram", "")).lower() in failed_diagram_names
                ]
                
                logger.info(f"Targeting {len(new_selected)} failed diagrams for repair: {failed_diagram_names}")
                # pyrefly: ignore [bad-assignment]
                state_updates["selected_uml_diagrams"] = new_selected
        
        return state_updates

# Automatically register the agent
AgentRegistry().register(UMLValidatorAgent())
