"""Planner Agent implementation."""

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

logger = get_logger("agents.planner")

class PlannerAgent(BaseAgent):
    """Planner agent responsible for generating an execution plan based on user intent."""
    
    @property
    def name(self) -> str:
        return "Planner"
        
    @property
    def description(self) -> str:
        return "Generates an ordered execution plan of agents based on intent."
        
    @property
    def capabilities(self) -> List[str]:
        return ["workflow_planning", "agent_orchestration"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Planner agent step."""
        user_request = state.get("user_request", "").strip()
        intent_info = state.get("intent_classification", {})
        
        logger.info("Planner starting execution...", extra={"user_request": user_request})
        
        if not user_request:
            raise ValueError("State validation failed: user_request is empty.")
            
        registry = AgentRegistry()
        available_agents = registry.list_agents()
        agents_info = []
        for agent_name in available_agents:
            agent = registry.get(agent_name)
            if agent:
                agents_info.append(
                    f"- {agent.name}: {agent.description} (Capabilities: {', '.join(agent.capabilities)})"
                )
                
        agents_context = "\n".join(agents_info)
        
        system_prompt = f"""You are a Workflow Planner for an AI engineering platform.
Based on the User's Request and the identified Intent, your task is to choose the optimal ordered sequence of agents to fulfill the request.
"""
        
        impact_report = state.get("impact_analysis_report", {})
        if impact_report and impact_report.get("affected_diagrams"):
            system_prompt += f"""
An Impact Analysis has been completed.
Affected Diagrams: {impact_report.get('affected_diagrams')}
Reuse Diagrams: {impact_report.get('reuse_diagrams')}

DO NOT regenerate everything. Only schedule agents necessary to regenerate the affected diagrams.
"""

        system_prompt += f"""
Available Agents:
{agents_context}

CRITICAL INSTRUCTION:
If the user requests Architecture Design or UML Diagram Generation, and NO impact analysis restricts you, you MUST output this EXACT sequence of agents:
[
    "Requirement Extraction Agent",
    "Architecture Reasoning Agent",
    "UML Recommendation Agent",
    "UML Generator",
    "UML Validator",
    "Renderer Agent"
]

Output ONLY a valid JSON array of strings, where each string is the exact name of an agent from the available list. Choose ONLY the required agents. Provide the list in the exact order they should be executed.

Example:
[
    "Requirement Analyst",
    "Solution Architect"
]

Do NOT include any other text, markdown formatting, or explanation.
"""

        human_content = f"User Request: {user_request}\nIdentified Intent: {json.dumps(intent_info)}"
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_content)
        ]
        
        logger.info("Invoking LLM for Planner...")
        llm_response = self.llm.invoke(messages)
        
        response_content = llm_response.content
        if isinstance(response_content, list):
            response_content = "\n".join([str(item) for item in response_content])
        else:
            response_content = str(response_content)
            
        clean_content = response_content.replace("```json", "").replace("```", "").strip()
        
        try:
            execution_plan = json.loads(clean_content)
            if not isinstance(execution_plan, list):
                execution_plan = []
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {clean_content}")
            execution_plan = []
            
        logger.info(f"Execution plan generated: {execution_plan}")
        
        new_message = AIMessage(
            content=json.dumps(execution_plan, indent=2),
            name="planner"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "planning_completed": True,
            "last_updated": generate_timestamp()
        }
        
        state_updates = {
            "execution_plan": execution_plan,
            "messages": [new_message],
            "metadata": updated_metadata
        }
        
        return state_updates

# Automatically register the agent
AgentRegistry().register(PlannerAgent())
