"""UML Repair Agent implementation."""

import json
from typing import Dict, Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.base import BaseAgent
from core.providers.factory import LLMFactory
from core.agent_registry import AgentRegistry
from app.state import ForgeState
from config.logging import get_logger
from core.utils import generate_timestamp

logger = get_logger("agents.uml_repair")

class UMLRepairAgent(BaseAgent):
    """UML Repair Agent responsible for fixing PlantUML syntax based on compiler errors."""
    
    @property
    def name(self) -> str:
        return "UML Repair Agent"
        
    @property
    def description(self) -> str:
        return "Repairs PlantUML syntax errors based on compiler feedback without altering semantics."
        
    @property
    def capabilities(self) -> List[str]:
        return ["plantuml_repair", "syntax_correction"]

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
            self._llm = LLMFactory.create_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the UML Repair Agent step."""
        validation_report = state.get("plantuml_validation_report", {})
        diagrams_content = state.get("plantuml_diagrams", {})
        
        if not validation_report or not diagrams_content:
            logger.warning("No validation report or diagrams found for repair.")
            return {}
            
        diagram_results = validation_report.get("diagram_results", [])
        failed_diagrams = [d for d in diagram_results if not d.get("valid", True)]
        
        if not failed_diagrams:
            logger.info("No failed diagrams found for repair. Exiting repair agent.")
            return {}
            
        logger.info(f"UML Repair starting execution for {len(failed_diagrams)} failed diagrams...")
        
        current_metadata = state.get("metadata", {}) or {}
        repair_attempts = current_metadata.get("repair_attempts", 0) + 1
        
        system_prompt = """You are a highly specialized UML Repair Agent.
Your task is to fix syntax errors in PlantUML code based on compiler output.

Rules:
1. Fix ONLY the syntax errors identified by the compiler.
2. Do NOT redesign the architecture or change the semantics.
3. Do NOT rename components unless strictly necessary to fix a syntax error (e.g., escaping spaces).
4. Do NOT include markdown code fences (like ```plantuml) in your output, just return the raw PlantUML code.
5. You must output exactly the corrected PlantUML file content and absolutely nothing else.
"""

        repaired_diagrams_count = 0
        updated_diagrams_content = dict(diagrams_content)
        
        for failed_diag in failed_diagrams:
            diag_name = failed_diag.get("diagram", "")
            if diag_name not in diagrams_content:
                continue
                
            original_puml = diagrams_content[diag_name]
            compiler_stderr = failed_diag.get("stderr", "")
            
            user_prompt = f"""The following PlantUML failed compilation.

Diagram Name: {diag_name}

Compiler error:
{compiler_stderr}

Original PlantUML:
{original_puml}

Fix ONLY the syntax. Preserve semantics. Return ONLY the corrected PlantUML code."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            logger.info(f"Invoking LLM for repairing {diag_name}...")
            llm_response = self.llm.invoke(messages)
            
            response_content = llm_response.content
            if isinstance(response_content, list):
                response_content = "\n".join([str(item) for item in response_content])
            elif not isinstance(response_content, str):
                response_content = str(response_content)
                
            clean_content = response_content.replace("```plantuml", "").replace("```puml", "").replace("```", "").strip()
            
            updated_diagrams_content[diag_name] = clean_content
            repaired_diagrams_count += 1
            logger.info(f"Successfully applied repair patch for {diag_name}.")
            
        logger.info(f"UML Repair completed {repaired_diagrams_count} repairs. Attempt count: {repair_attempts}")
        
        new_message = AIMessage(
            content=f"Attempted {repaired_diagrams_count} repairs (Repair Attempt {repair_attempts}).",
            name="uml_repair"
        )
        
        updated_metadata = {
            **current_metadata,
            "repair_attempts": repair_attempts,
            "uml_repair_completed": True,
            "last_updated": generate_timestamp()
        }
        
        return {
            "plantuml_diagrams": updated_diagrams_content,
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_repair"
        }

# Automatically register the agent
AgentRegistry().register(UMLRepairAgent())
