"""UML Recommendation Agent implementation."""

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

logger = get_logger("agents.uml_recommendation")

class UMLRecommendationAgent(BaseAgent):
    """Recommends necessary UML diagrams with AI-driven reasoning."""
    
    @property
    def name(self) -> str:
        return "UML Recommendation Agent"
        
    @property
    def description(self) -> str:
        return "Analyzes architecture and determines strictly which UML diagrams are required with deep reasoning."
        
    @property
    def capabilities(self) -> List[str]:
        return ["uml_recommendation", "architecture_reasoning"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the UML Recommendation Agent."""
        logger.info("UML Recommendation Agent starting execution.")
        
        user_request = state.get("user_request", "")
        # Assuming architecture is populated by Architecture Reasoning Agent
        architecture = state.get("architecture", "No structured architecture found.")
        
        system_prompt = """You are a Principal Software Architect.
Read the provided architecture description. Decide exactly which UML diagrams are required to visualize it properly.
Supported UML: Use Case, Activity, Sequence, Communication, Class, Object, Component, Deployment, Package, Composite Structure, State Machine, Timing, Interaction Overview, Profile.

You MUST NOT hardcode rules. Use deep architectural reasoning.
Output ONLY valid JSON matching this exact structure:
{
    "selected_diagrams": [
        {
            "diagram": "Diagram Name",
            "confidence": 0.95,
            "reason": "Explicit architectural reason."
        }
    ],
    "rejected_diagrams": [
        {
            "diagram": "Diagram Name",
            "reason": "Explicit reason why it is unnecessary."
        }
    ]
}

DO NOT include markdown tags or explanation. Output ONLY the JSON.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Request: {user_request}\n\nArchitecture Context:\n{architecture}")
        ]
        
        logger.info("Invoking LLM for UML Recommendation...")
        llm_response = self.llm.invoke(messages)
        
        response_content = str(llm_response.content).replace("```json", "").replace("```", "").strip()
        
        try:
            recommendation_report = json.loads(response_content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {response_content}")
            recommendation_report = {"selected_diagrams": [], "rejected_diagrams": []}
            
        logger.info(f"UML Recommendation Generated: {len(recommendation_report.get('selected_diagrams', []))} diagrams selected.")
        
        new_message = AIMessage(
            content=json.dumps(recommendation_report, indent=2),
            name="uml_recommendation"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "uml_recommendation_completed": True,
            "last_updated": generate_timestamp()
        }
        
        return {
            "uml_recommendation_report": recommendation_report,
            "selected_uml_diagrams": recommendation_report.get("selected_diagrams", []),
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_recommendation"
        }

AgentRegistry().register(UMLRecommendationAgent())
