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
        return ["uml_validation", "syntax_checking"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the UML Validator agent step."""
        artifacts = cast(Dict[str, List[str]], state.get("artifacts", {}))
        uml_paths = artifacts.get("uml", [])
        
        if not uml_paths:
            logger.warning("No UML diagrams found in artifacts to validate.")
            return {}
            
        logger.info(f"UML Validator starting execution for {len(uml_paths)} diagrams...")
        
        diagrams_content = {}
        for path in uml_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    diagrams_content[path] = f.read()
            except Exception as e:
                logger.error(f"Failed to read UML diagram at {path}: {e}")
                
        if not diagrams_content:
            return {}

        system_prompt = """You are a specialized UML Validator Agent.
Your task is to validate the provided PlantUML syntax for structural correctness.
Check for:
1. Missing @startuml or @enduml tags.
2. Malformed syntax (e.g., unclosed brackets, missing arrows, invalid aliases).
3. Invalid characters or unsupported directives.

Respond ONLY with a valid JSON object matching this schema:
{
  "valid": boolean,
  "report": "Detailed validation report",
  "errors": ["List of specific errors if any"]
}

Do NOT include any other text, explanations, or markdown formatting blocks (like ```json). Just output raw JSON.
"""
        
        # Format the diagrams for the prompt
        content_to_validate = ""
        for path, content in diagrams_content.items():
            content_to_validate += f"--- Diagram: {path} ---\n{content}\n\n"
            
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
            validation_result = json.loads(clean_content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {clean_content}")
            validation_result = {
                "valid": False,
                "report": "Failed to parse validation response.",
                "errors": ["JSON parse error"]
            }
            
        is_valid = validation_result.get("valid", False)
        
        logger.info(f"UML Validation completed. Valid: {is_valid}")
        
        new_message = AIMessage(
            content=json.dumps(validation_result, indent=2),
            name="uml_validator"
        )
        
        current_metadata = cast(Dict[str, Any], state.get("metadata", {}))
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
        
        return state_updates

# Automatically register the agent
AgentRegistry().register(UMLValidatorAgent())
