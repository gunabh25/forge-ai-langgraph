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
        
    @property
    def requires(self) -> List[str]:
        """The inputs required by this agent. Default is empty for backward compatibility."""
        return []
        
    @property
    def produces(self) -> List[str]:
        """The outputs produced by this agent. Default is empty for backward compatibility."""
        return []
        
    @abstractmethod
    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the agent step."""
        pass
