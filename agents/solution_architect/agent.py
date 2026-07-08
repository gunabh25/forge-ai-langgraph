"""Solution Architect Agent implementation."""

import json
from typing import Dict, Any, Optional, List
from agents.base import BaseAgent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from core.llm import get_llm
from core.prompts import load_prompt, load_examples
from app.state import ForgeState
from config.logging import get_logger
from core.constants import WorkflowStages, ApprovalStatuses, ArtifactFolders, ArtifactNames
from core.utils import generate_timestamp
from core.artifact_manager import ArtifactManager

logger = get_logger("agents.solution_architect")

class SolutionArchitectAgent(BaseAgent):
    """Solution Architect agent responsible for generating the Architecture Specification."""
    
    @property
    def name(self) -> str:
        return "Solution Architect"
        
    @property
    def description(self) -> str:
        return "Responsible for generating the Architecture Specification."
        
    @property
    def capabilities(self) -> List[str]:
        return ["architecture_design", "system_modeling"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm
        
    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Solution Architect Agent."""
        logger.info("Solution Architect Agent starting execution.")
        
        requirements_json = state.get("requirements_json", {})
        if not requirements_json:
            logger.warning("No requirements_json found in state.")
        
        system_prompt = """You are a Senior Software Architect.
Read the structured requirements JSON and reason about the system architecture.
Output ONLY valid JSON matching this exact structure:
{
    "architecture_pattern": "Microservices",
    "services": [{"name": "Auth Service", "responsibility": "Handles identity"}],
    "modules": ["User Management", "Billing"],
    "database": "PostgreSQL",
    "authentication": "OAuth2",
    "communication": "REST",
    "deployment": "Docker",
    "scalability": "Horizontal",
    "security": ["TLS encryption", "Role-based access"],
    "cache": "Redis",
    "event_flow": ["User Registers -> Auth Service -> Event Bus -> Email Service"],
    "external_integrations": ["Stripe API", "AWS S3"]
}

DO NOT generate UML syntax. DO NOT output paragraphs. Output ONLY the JSON.
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
            name="solution_architect"
        )
        
        return {
            "architecture_json": architecture_json,
            "architecture": json.dumps(architecture_json, indent=2),
            "messages": [new_message],
            "current_stage": "solution_architect"
        }


# Automatically register the agent
from core.agent_registry import AgentRegistry
AgentRegistry().register(SolutionArchitectAgent())
