"""Impact Analysis Agent implementation."""

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

logger = get_logger("agents.impact_analysis")

class ImpactAnalysisAgent(BaseAgent):
    """Impact Analysis Agent for iterative software design updates."""
    
    @property
    def name(self) -> str:
        return "Impact Analysis Agent"
        
    @property
    def description(self) -> str:
        return "Analyzes iterative prompts to detect changed components and identify which UML diagrams need regeneration."
        
    @property
    def capabilities(self) -> List[str]:
        return ["impact_analysis", "incremental_update"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Impact Analysis Agent."""
        logger.info("Impact Analysis Agent starting execution.")
        
        user_request = state.get("user_request", "")
        architecture = state.get("architecture", "")
        uml_recommendation = state.get("uml_recommendation_report", {})
        
        if not architecture or not uml_recommendation:
            logger.info("No prior architecture or UML recommendations found. Skipping impact analysis.")
            return {}

        system_prompt = """You are a Senior Architect determining the blast radius of a new requirement.
Compare the user's new request against the previous architecture and UML recommendations.
Detect changed components, affected diagrams (must regenerate), and diagrams that can be safely reused.

Output ONLY valid JSON matching this exact structure:
{
    "changed_components": ["Component A"],
    "affected_diagrams": ["Component", "Deployment"],
    "reuse_diagrams": ["Use Case", "Activity"],
    "reason": "Explicit reasoning."
}

DO NOT include markdown tags or explanation. Output ONLY the JSON.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"New User Request: {user_request}\n\nPrevious Architecture:\n{architecture}\n\nPrevious UML Recommendations:\n{json.dumps(uml_recommendation)}")
        ]
        
        logger.info("Invoking LLM for Impact Analysis...")
        llm_response = self.llm.invoke(messages)
        
        response_content = str(llm_response.content).replace("```json", "").replace("```", "").strip()
        
        try:
            impact_report = json.loads(response_content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {response_content}")
            impact_report = {
                "changed_components": [],
                "affected_diagrams": [],
                "reuse_diagrams": [],
                "reason": "Failed to generate valid impact analysis JSON."
            }
            
        logger.info(f"Impact Analysis Complete. Affected diagrams: {impact_report.get('affected_diagrams', [])}")
        
        new_message = AIMessage(
            content=json.dumps(impact_report, indent=2),
            name="impact_analysis"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "impact_analysis_completed": True,
            "last_updated": generate_timestamp()
        }
        
        return {
            "impact_analysis_report": impact_report,
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "impact_analysis"
        }

AgentRegistry().register(ImpactAnalysisAgent())
