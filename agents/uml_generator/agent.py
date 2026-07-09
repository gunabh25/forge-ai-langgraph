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
            "Component", "Sequence", "Activity", "Deployment", "Class", "Use Case"
        ]

    @property
    def requires(self) -> List[str]:
        return ["architecture_json", "selected_uml_diagrams"]

    @property
    def produces(self) -> List[str]:
        return ["plantuml_diagrams"]

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
        current_diagram_id = state.get("current_diagram_id")
        
        if not selected_uml_diagrams:
            logger.warning("No UML diagrams selected for generation.")
            return {}
            
        if current_diagram_id:
            diagrams_to_process = [d for d in selected_uml_diagrams if d.get("diagram_id", d.get("diagram", d.get("type", "unknown"))) == current_diagram_id]
            logger.info(f"UML Generator starting parallel generation for diagram: {current_diagram_id}")
        else:
            diagrams_to_process = selected_uml_diagrams
            logger.info(f"UML Generator starting sequential generation for {len(selected_uml_diagrams)} diagrams...")
        
        # Initialize from existing state
        diagrams = dict(state.get("plantuml_diagrams", {}) or {})
        saved_paths = list(state.get("artifacts", {}).get("uml", []) or [])
        diagram_states = dict(state.get("diagram_execution_states", {}) or {})
        
        import hashlib
        import time
        arch_str = json.dumps(architecture_json, sort_keys=True)
        arch_hash = hashlib.md5(arch_str.encode("utf-8")).hexdigest()
        
        for diagram_info in diagrams_to_process:
            diagram_type = diagram_info.get("diagram", diagram_info.get("type", "unknown"))
            diag_id = diagram_info.get("diagram_id", diagram_type)
            reason = diagram_info.get("reason", "")
            
            cache_key = f"{arch_hash}_{diag_id}"
            
            # Simple in-memory cache check (could be expanded to persistent cache)
            # For now we'll just track if it's already in diagram_states and successful
            existing_state = diagram_states.get(diag_id, {})
            if existing_state.get("status") == "success" and existing_state.get("generator_output"):
                # Cache hit!
                logger.info(f"Cache hit for {diag_id}. Skipping generation.")
                continue
                
            start_time = time.time()
            
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
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            clean_content = str(llm_response.content).replace("```plantuml", "").replace("```puml", "").replace("```", "").strip()
            
            diagrams[diag_id] = clean_content
            
            base_name = diag_id.lower().replace(" ", "_")
            saved_path = self.artifact_manager.save_artifact(
                stage="uml",
                base_name=base_name,
                content=clean_content,
                ext="puml"
            )
            if saved_path not in saved_paths:
                saved_paths.append(saved_path)
                
            # Update DiagramExecutionState
            new_diag_state = {
                "diagram_id": diag_id,
                "diagram_type": diagram_type,
                "status": "generated",
                "attempt": existing_state.get("attempt", 0) + 1,
                "generator_output": clean_content,
                "execution_time_ms": existing_state.get("execution_time_ms", 0) + generation_time_ms,
                "llm_calls": existing_state.get("llm_calls", 0) + 1
            }
            diagram_states[diag_id] = new_diag_state
            
        new_message = AIMessage(
            content=f"Generated {len(diagrams_to_process)} diagrams.",
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
            "diagram_execution_states": diagram_states,
            "artifacts": {
                "uml": saved_paths
            },
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_generator"
        }

# Automatically register the agent
AgentRegistry().register(UMLGeneratorAgent())
