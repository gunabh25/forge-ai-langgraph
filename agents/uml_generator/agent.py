"""UML Generator Agent implementation."""

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
from core.artifact_manager import ArtifactManager

logger = get_logger("agents.uml_generator")

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
        return [
            "sequence_diagram", 
            "component_diagram", 
            "class_diagram", 
            "activity_diagram", 
            "deployment_diagram", 
            "package_diagram"
        ]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        self.artifact_manager = ArtifactManager()
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the UML Generator agent step."""
        user_request = state.get("user_request", "").strip()
        # Fallback to look for a specific uml_request or prompt
        uml_request = cast(Dict[str, Any], state.get("uml_request", {}) if isinstance(state.get("uml_request"), dict) else {})
        prompt = str(uml_request.get("prompt", user_request))
        diagram_types = cast(list, state.get("diagram_types") or uml_request.get("diagram_types", []))
        
        if not prompt:
            raise ValueError("State validation failed: prompt is empty.")
            
        logger.info("UML Generator starting execution...", extra={"prompt": prompt, "diagram_types": diagram_types})
        
        types_text = ", ".join(diagram_types) if diagram_types else "Sequence Diagram, Component Diagram, Class Diagram, Activity Diagram, Deployment Diagram, Package Diagram"
        
        system_prompt = f"""You are a specialized UML Generator Agent.
Your task is to generate PlantUML syntax for the following requested diagram types based on the user's prompt: {types_text}.

You must ONLY generate valid PlantUML code. Do NOT render images.
Respond ONLY with a valid JSON object where keys are the diagram types and values are the corresponding PlantUML syntax strings. The PlantUML strings must start with @startuml and end with @enduml.

Example format:
{{
  "Sequence Diagram": "@startuml\\nAlice -> Bob: Request\\n@enduml",
  "Class Diagram": "@startuml\\nclass User {{\\n}}\\n@enduml"
}}

Do NOT include any other text, explanations, or markdown formatting blocks (like ```json). Just output raw JSON.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Prompt: {prompt}")
        ]
        
        logger.info("Invoking LLM for UML generation...")
        llm_response = self.llm.invoke(messages)
        
        response_content = llm_response.content
        if isinstance(response_content, list):
            response_content = "\n".join([str(item) for item in response_content])
        elif not isinstance(response_content, str):
            response_content = str(response_content)
            
        clean_content = response_content.replace("```json", "").replace("```", "").strip()
        
        try:
            diagrams = json.loads(clean_content)
            if not isinstance(diagrams, dict):
                diagrams = {}
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {clean_content}")
            diagrams = {}
            
        logger.info(f"Generated {len(diagrams)} diagrams.")
        
        # Save artifacts
        saved_paths = []
        for d_type, d_content in diagrams.items():
            base_name = d_type.lower().replace(" ", "_")
            saved_path = self.artifact_manager.save_artifact(
                stage="uml",
                base_name=base_name,
                content=d_content,
                ext="puml"
            )
            saved_paths.append(saved_path)
            
        new_message = AIMessage(
            content=json.dumps(diagrams, indent=2),
            name="uml_generator"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "uml_generation_completed": True,
            "last_updated": generate_timestamp()
        }
        
        state_updates = {
            "artifacts": {
                "uml": saved_paths
            },
            "messages": [new_message],
            "metadata": updated_metadata
        }
        
        return state_updates

# Automatically register the agent
AgentRegistry().register(UMLGeneratorAgent())
