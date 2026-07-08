"""Requirement Extraction Agent implementation."""

import json
from typing import Dict, Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.base import BaseAgent
from core.llm import get_llm
from core.agent_registry import AgentRegistry
from app.state import ForgeState
from config.logging import get_logger

logger = get_logger("agents.requirement_extraction")

class RequirementExtractionAgent(BaseAgent):
    """Requirement Extraction Agent responsible for structuring user requirements."""
    
    @property
    def name(self) -> str:
        return "Requirement Extraction Agent"
        
    @property
    def description(self) -> str:
        return "Extracts structured functional and non-functional requirements, actors, services, workflows, and databases."
        
    @property
    def capabilities(self) -> List[str]:
        return ["requirement_extraction", "structured_analysis"]

    @property
    def requires(self) -> List[str]:
        return []

    @property
    def produces(self) -> List[str]:
        return ["requirements_json"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Requirement Extraction Agent."""
        logger.info("Requirement Extraction Agent starting execution.")
        
        user_request = state.get("user_request", "")
        
        system_prompt = """You are a Principal Requirement Analyst.
Analyze the user's request and extract structured requirements for a software system.
Identify functional requirements, non-functional requirements, actors, external systems, APIs, services, databases, business workflows, constraints, and assumptions.

Output ONLY valid JSON matching this exact structure:
{
    "functional_requirements": ["Req 1", "Req 2"],
    "non_functional_requirements": ["Req 1", "Req 2"],
    "actors": ["User", "Admin"],
    "services": ["Auth Service", "Payment Service"],
    "apis": ["Stripe API", "Google Maps API"],
    "external_systems": ["Stripe", "AWS S3"],
    "databases": ["PostgreSQL", "Redis"],
    "workflows": ["User Login", "Checkout Process"],
    "constraints": ["Must deploy to AWS", "Must use Python 3"],
    "assumptions": ["Users have internet access"]
}

DO NOT include markdown tags or explanation. Output ONLY the JSON.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Request: {user_request}")
        ]
        
        logger.info("Invoking LLM for Requirement Extraction...")
        llm_response = self.llm.invoke(messages)
        
        response_content = str(llm_response.content).replace("```json", "").replace("```", "").strip()
        
        try:
            requirements_json = json.loads(response_content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {response_content}")
            requirements_json = {}
            
        logger.info("Requirement Extraction Complete.")
        
        new_message = AIMessage(
            content=json.dumps(requirements_json, indent=2),
            name="requirement_extraction"
        )
        
        return {
            "requirements_json": requirements_json,
            "messages": [new_message],
            "current_stage": "requirement_extraction"
        }

AgentRegistry().register(RequirementExtractionAgent())
