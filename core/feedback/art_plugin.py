"""Abstract Interfaces for future ART (Active Reinforcement / Reasoning Tuning) Plugins."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.feedback.models import UserFeedbackEntry

class ARTPluginInterface(ABC):
    """
    Interface for integrating ART (Active Reinforcement Training) plugins.
    Currently a stub; implement this interface to connect to RL agents,
    reward modeling endpoints, or external alignment systems.
    """
    
    @abstractmethod
    def process_feedback(self, entry: UserFeedbackEntry) -> None:
        """Process the incoming feedback for reinforcement learning or alignment."""
        pass
        
    @abstractmethod
    def generate_reward_score(self, entry: UserFeedbackEntry) -> float:
        """Calculate a reward score based on the feedback entry."""
        pass
        
    @abstractmethod
    def get_plugin_status(self) -> Dict[str, Any]:
        """Return the health and configuration status of the ART plugin."""
        pass
