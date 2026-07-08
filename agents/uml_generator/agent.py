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
            "Component", "Sequence", "Activity", "Deployment", "Use Case",
            "Class", "Package", "State Machine", "Communication", "Object",
            "Timing", "Profile", "Composite Structure", "Interaction Overview"
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
        architecture_json = state.get("architecture_json", {})
        selected_uml_diagrams = state.get("selected_uml_diagrams", [])
        
        if not selected_uml_diagrams:
            logger.warning("No UML diagrams selected for generation.")
            return {}
            
        logger.info(f"UML Generator starting iterative generation for {len(selected_uml_diagrams)} diagrams...")
        
        diagrams = {}
        saved_paths = []
        
        for diagram_info in selected_uml_diagrams:
            diagram_type = diagram_info.get("diagram")
            if not diagram_type:
                logger.warning(f"Missing diagram type in diagram_info: {diagram_info}")
                continue
            
            reason = diagram_info.get("reason", "")
            
            system_prompt = f"""You are a specialized UML Generator Agent.
Your task is to generate valid PlantUML syntax for a {diagram_type} based on the user's request and the provided architecture JSON.
Reason for this diagram: {reason}

CRITICAL RULES:
1. Generate EXACTLY ONE PlantUML diagram. Never combine multiple diagrams.
2. You must ONLY generate valid PlantUML code. Do NOT render images.
3. Respond ONLY with the raw PlantUML syntax string. The string must start with @startuml and end with @enduml.
4. DO NOT include markdown formatting blocks (like ```plantuml). Just output the raw syntax.
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User Request: {user_request}\n\nArchitecture JSON:\n{json.dumps(architecture_json, indent=2)}")
            ]
            
            logger.info(f"Generating {diagram_type}...")
            llm_response = self.llm.invoke(messages)
            
            clean_content = str(llm_response.content).replace("```plantuml", "").replace("```puml", "").replace("```", "").strip()
            
            diagrams[diagram_type] = clean_content
            
            base_name = diagram_type.lower().replace(" ", "_")
            saved_path = self.artifact_manager.save_artifact(
                stage="uml",
                base_name=base_name,
                content=clean_content,
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
        
        return {
            "plantuml_diagrams": diagrams,
            "artifacts": {
                "uml": saved_paths
            },
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_generator"
        }

# Automatically register the agent
AgentRegistry().register(UMLGeneratorAgent())
