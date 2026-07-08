"""Planner Agent implementation."""

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
        intent_info = cast(Dict[str, Any], state.get("intent_classification", {}))
        
        logger.info("Planner starting capability-driven execution...", extra={"user_request": user_request})
        
        if not user_request:
            raise ValueError("State validation failed: user_request is empty.")
            
        # Read required outputs, supporting both new root-level arrays and legacy workflow_specification formats
        required_outputs = intent_info.get("required_outputs", [])
        if not required_outputs:
            required_outputs = intent_info.get("workflow_specification", {}).get("required_outputs", [])
            
        if not required_outputs:
            logger.warning("No required_outputs found in intent. Falling back to default.")
            intent_name = intent_info.get("intent")
            if intent_name == "architecture_design":
                required_outputs = ["architecture_json"]
            else:
                required_outputs = ["rendered_svg_references"]
                
        # Gather available domain agents
        registry = AgentRegistry()
        available_agents = registry.list_agents()
        infrastructure_agents = {
            "Planner",
            "Intent Analyzer",
            "Conversation Memory",
            "Agent Registry",
            "Dynamic Executor",
            "Feedback Manager"
        }
        
        all_agents = []
        all_produced = set()
        for agent_name in available_agents:
            if agent_name in infrastructure_agents:
                continue
            agent = registry.get(agent_name)
            if agent:
                all_agents.append(agent)
                all_produced.update(agent.produces)
                
        # What is already provided by state?
        provided_outputs = set()
        for key, value in state.items():
            if value:
                provided_outputs.add(key)
                
        # Backward Chaining
        needed_outputs = {req for req in required_outputs if req in all_produced and req not in provided_outputs}
        selected_agents = set()
        
        while needed_outputs:
            progress = False
            for agent in all_agents:
                if agent in selected_agents:
                    continue
                produces = set(agent.produces)
                if produces.intersection(needed_outputs):
                    selected_agents.add(agent)
                    needed_outputs -= produces
                    
                    for req in agent.requires:
                        if req in all_produced and req not in provided_outputs:
                            needed_outputs.add(req)
                    progress = True
                    
            if not progress:
                logger.warning(f"Could not resolve dependencies for: {needed_outputs}")
                break
                
        # Topological Sort
        dependencies = {a: set() for a in selected_agents}
        for a in selected_agents:
            for req in a.requires:
                for b in selected_agents:
                    if req in b.produces:
                        dependencies[a].add(b)
                        
        sorted_plan = []
        visited = set()
        
        def visit(node, path):
            if node in path:
                return # cycle detected
            if node in visited:
                return
            path.add(node)
            for dep in dependencies[node]:
                visit(dep, path)
            path.remove(node)
            visited.add(node)
            sorted_plan.append(node)
            
        for a in selected_agents:
            visit(a, set())
            
        execution_plan = [a.name for a in sorted_plan]
        
        logger.info(f"Capability-driven execution plan generated: {execution_plan}")
        
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
        
        return {
            "execution_plan": execution_plan,
            "messages": [new_message],
            "metadata": updated_metadata
        }

# Automatically register the agent
AgentRegistry().register(PlannerAgent())
