"""UML Validator Agent implementation."""

import json
from typing import Dict, Any, List, Optional, cast
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.base import BaseAgent
from core.llm import get_llm
from core.agent_registry import AgentRegistry
from app.state import ForgeState
from config.logging import get_logger
from core.utils import generate_timestamp

logger = get_logger("agents.uml_validator")

class UMLValidatorAgent(BaseAgent):
    """UML Validator agent responsible for checking PlantUML diagrams."""
    
    @property
    def name(self) -> str:
        return "UML Validator"
        
    @property
    def description(self) -> str:
        return "Validates PlantUML syntax, detects malformed diagrams, and generates a validation report."
        
    @property
    def capabilities(self) -> List[str]:
        return ["plantuml_validation", "syntax_checking"]

    @property
    def requires(self) -> List[str]:
        return ["plantuml_diagrams"]

    @property
    def produces(self) -> List[str]:
        return ["plantuml_validation_report"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the UML Validator agent step."""
        diagrams_content = state.get("plantuml_diagrams", {})
        
        if not diagrams_content:
            logger.warning("No PlantUML diagrams found in state to validate.")
            return {}
            
        logger.info(f"UML Validator starting execution for {len(diagrams_content)} diagrams...")

        system_prompt = """You are a specialized UML Validator Agent.
Your task is to validate the provided PlantUML syntax for structural correctness.
Check for:
1. PlantUML syntax
2. participant aliases
3. duplicate names
4. invalid arrows
5. unclosed blocks
6. invalid relationships

Respond ONLY with a valid JSON object matching this schema:
{
  "valid": boolean,
  "report": "Detailed validation report",
  "diagram_results": [
    {
      "diagram": "component",
      "valid": boolean,
      "errors": ["List of specific errors if any"]
    }
  ]
}

Do NOT include any other text, explanations, or markdown formatting blocks (like ```json). Just output raw JSON.
"""
        
        # Format the diagrams for the prompt
        content_to_validate = ""
        for name, content in diagrams_content.items():
            content_to_validate += f"--- Diagram: {name} ---\n{content}\n\n"
            
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Please validate the following diagrams:\n\n{content_to_validate}")
        ]
        
        logger.info("Invoking LLM for UML validation...")
        llm_response = self.llm.invoke(messages)
        
        response_content = llm_response.content
        if isinstance(response_content, list):
            response_content = "\n".join([str(item) for item in response_content])
        elif not isinstance(response_content, str):
            response_content = str(response_content)
            
        clean_content = response_content.replace("```json", "").replace("```", "").strip()
        
        try:
            validation_result = cast(Dict[str, Any], json.loads(clean_content))
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {clean_content}")
            validation_result = {
                "valid": False,
                "report": "Failed to parse validation response.",
                "diagram_results": []
            }
            
        is_valid = validation_result.get("valid", False)
        
        logger.info(f"UML Validation completed. Valid: {is_valid}")
        
        new_message = AIMessage(
            content=json.dumps(validation_result, indent=2),
            name="uml_validator"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "uml_validation_completed": True,
            "uml_is_valid": is_valid,
            "uml_validation_report": validation_result.get("report"),
            "retry_requested": not is_valid,
            "last_updated": generate_timestamp()
        }
        
        state_updates = {
            "plantuml_validation_report": validation_result,
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_validator"
        }
        
        # If validation fails, we want the executor to retry only the failed diagrams
        if not is_valid:
            # pyrefly: ignore [bad-assignment]
            diagram_results: List[Dict[str, Any]] = validation_result.get("diagram_results", [])
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
                
                logger.info(f"Targeting {len(new_selected)} failed diagrams for retry: {failed_diagram_names}")
                # pyrefly: ignore [bad-assignment]
                state_updates["selected_uml_diagrams"] = new_selected
        
        return state_updates

# Automatically register the agent
AgentRegistry().register(UMLValidatorAgent())
