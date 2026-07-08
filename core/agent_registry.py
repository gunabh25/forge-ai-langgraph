"""Agent Registry for managing ForgeAI agents."""

from typing import Dict, List, Optional
from agents.base import BaseAgent

class AgentRegistry:
    """Singleton registry for managing agents."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentRegistry, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        if not hasattr(self, '_agents'):
            self._agents: Dict[str, BaseAgent] = {}
        
    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance."""
        if not isinstance(agent, BaseAgent):
            raise ValueError("Agent must be an instance of BaseAgent")
        self._agents[agent.name] = agent
        
    def unregister(self, agent_name: str) -> None:
        """Unregister an agent by name."""
        if agent_name in self._agents:
            del self._agents[agent_name]
            
    def get(self, agent_name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self._agents.get(agent_name)
        
    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())
        
    def find_by_capability(self, capability: str) -> List[BaseAgent]:
        """Find agents that have a specific capability."""
        return [
            agent for agent in self._agents.values() 
            if capability in agent.capabilities
        ]
