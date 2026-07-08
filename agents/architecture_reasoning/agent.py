"""Architecture Reasoning Agent implementation."""

import json
from typing import Dict, Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.base import BaseAgent
from core.llm import get_llm
from core.agent_registry import AgentRegistry
from app.state import ForgeState
from config.logging import get_logger

logger = get_logger("agents.architecture_reasoning")

class ArchitectureReasoningAgent(BaseAgent):
    """Architecture Reasoning Agent responsible for structured software design."""
    
    @property
    def name(self) -> str:
        return "Architecture Reasoning Agent"
        
    @property
    def description(self) -> str:
        return "Reasons about services, boundaries, communication, persistence, deployment, and scalability."
        
    @property
    def capabilities(self) -> List[str]:
        return ["architecture_design", "system_modeling"]

    @property
    def requires(self) -> List[str]:
        return ["requirements_json"]

    @property
    def produces(self) -> List[str]:
        return ["architecture_json"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Architecture Reasoning Agent."""
        logger.info("Architecture Reasoning Agent starting execution.")
        
        requirements_json = state.get("requirements_json", {})
        
        system_prompt = """You are a Principal Software Architect.
Read the structured requirements JSON and reason about the system architecture.
Design the services, module boundaries, communication patterns, persistence layer, deployment topology, and scalability strategies.

Output ONLY valid JSON matching this exact structure:
{
    "services": [{"name": "Auth Service", "responsibility": "Handles identity"}],
    "boundaries": ["API Gateway -> Microservices"],
    "communication": ["REST", "Kafka Event Driven"],
    "persistence": ["PostgreSQL for transactions", "Redis for cache"],
    "deployment": ["Kubernetes cluster", "AWS RDS"],
    "scalability": ["Horizontal auto-scaling for Web layer"]
}

DO NOT generate UML syntax. Output ONLY the JSON.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Requirements:\n{json.dumps(requirements_json, indent=2)}")
        ]
        
        logger.info("Invoking LLM for Architecture Reasoning...")
        llm_response = self.llm.invoke(messages)
        
        response_content = str(llm_response.content).replace("```json", "").replace("```", "").strip()
        
        try:
            architecture_json = json.loads(response_content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {response_content}")
            architecture_json = {}
            
        logger.info("Architecture Reasoning Complete.")
        
        new_message = AIMessage(
            content=json.dumps(architecture_json, indent=2),
            name="architecture_reasoning"
        )
        
        return {
            "architecture_json": architecture_json,
            "architecture": json.dumps(architecture_json, indent=2), # Keep backward compatibility
            "messages": [new_message],
            "current_stage": "architecture_reasoning"
        }

AgentRegistry().register(ArchitectureReasoningAgent())
