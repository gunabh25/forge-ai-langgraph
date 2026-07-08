from abc import ABC, abstractmethod
from typing import Dict, Any, List

from app.state import ForgeState

class BaseAgent(ABC):
    """Base class for all agents in ForgeAI."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the agent."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """The description of the agent."""
        pass
        
    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """The capabilities of the agent."""
        pass
        
    @abstractmethod
    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the agent step."""
        pass
