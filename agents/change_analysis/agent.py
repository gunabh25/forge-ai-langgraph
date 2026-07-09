"""Change Analysis Agent implementation."""

import json
from typing import Dict, Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.base import BaseAgent
from core.llm import get_llm
from core.agent_registry import AgentRegistry
from app.state import ForgeState
from config.logging import get_logger
from core.utils import generate_timestamp

logger = get_logger("agents.change_analysis")

class ChangeAnalysisAgent(BaseAgent):
    """Change Analysis Agent for incremental software design updates."""
    
    @property
    def name(self) -> str:
        return "Change Analysis Agent"
        
    @property
    def description(self) -> str:
        return "Analyzes iterative prompts to detect changed components and identify which UML diagrams need regeneration."
        
    @property
    def capabilities(self) -> List[str]:
        return ["change_analysis", "incremental_update"]

    @property
    def requires(self) -> List[str]:
        return ["user_request"]

    @property
    def produces(self) -> List[str]:
        return ["change_analysis_report"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Change Analysis Agent."""
        logger.info("Change Analysis Agent starting execution.")
        
        user_request = state.get("user_request", "")
        architecture = state.get("previous_architecture", {})
        previous_diagrams = state.get("previous_diagrams", {})
        
        # If no previous architecture, this is a brand new project.
        if not architecture:
            logger.info("No prior architecture found. This is a new project.")
            report = {
                "change_type": "new_project",
                "affected_requirements": [],
                "affected_services": [],
                "affected_diagrams": [],
                "requires_architecture_update": True,
                "requires_requirement_update": True
            }
            return self._finalize(state, report)

        system_prompt = """You are a Senior Architect determining the blast radius of a new requirement for an incremental update.
Compare the user's new request against the previous architecture and identify EXACTLY what changes.

Output ONLY valid JSON matching this exact structure:
{
    "change_type": "<e.g. minor_update, major_redesign, ui_only>",
    "affected_requirements": ["Requirement 1"],
    "affected_services": ["Auth Service"],
    "affected_diagrams": ["Component Diagram", "Deployment Diagram"],
    "requires_architecture_update": true,
    "requires_requirement_update": false
}

DO NOT include markdown tags or explanation. Output ONLY the JSON.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"New User Request: {user_request}\n\nPrevious Architecture:\n{json.dumps(architecture)}\n\nPrevious UML Diagrams Available:\n{list(previous_diagrams.keys())}")
        ]
        
        logger.info("Invoking LLM for Change Analysis...")
        llm_response = self.llm.invoke(messages)
        
        response_content = str(llm_response.content).replace("```json", "").replace("```", "").strip()
        
        try:
            impact_report = json.loads(response_content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {response_content}")
            impact_report = {
                "change_type": "unknown",
                "affected_requirements": [],
                "affected_services": [],
                "affected_diagrams": [],
                "requires_architecture_update": True,
                "requires_requirement_update": True
            }
            
        logger.info(f"Change Analysis Complete. Type: {impact_report.get('change_type')}, Affected diagrams: {impact_report.get('affected_diagrams', [])}")
        return self._finalize(state, impact_report)

    def _finalize(self, state: ForgeState, report: Dict[str, Any]) -> Dict[str, Any]:
        new_message = AIMessage(
            content=json.dumps(report, indent=2),
            name="change_analysis"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "change_analysis_completed": True,
            "last_updated": generate_timestamp()
        }
        
        return {
            "change_analysis_report": report,
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "change_analysis"
        }

AgentRegistry().register(ChangeAnalysisAgent())
