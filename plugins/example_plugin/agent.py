"""Example Agent Plugin."""

from typing import Dict, Any, List
from agents.base import BaseAgent
from core.plugins.sdk import register_plugin
from app.state import ForgeState
import logging

logger = logging.getLogger("plugins.example_plugin")

@register_plugin(
    name="Example Plugin Agent",
    description="An example agent that demonstrates the ForgeAI Plugin SDK.",
    capabilities=["example_capability"],
    requires=["requirements"],
    produces=["example_output"]
)
class ExamplePluginAgent(BaseAgent):
    """A sample plugin agent to show how to use the Plugin SDK."""
    
    # We do not strictly need to define properties if they are passed in @register_plugin
    # but we can provide fallbacks if we want. The decorator will override these.
    
    @property
    def name(self) -> str:
        return "Fallback Name"
        
    @property
    def description(self) -> str:
        return "Fallback Description"
        
    @property
    def capabilities(self) -> List[str]:
        return []
        
    def run(self, state: ForgeState) -> Dict[str, Any]:
        """
        Execute the plugin step.
        """
        logger.info("Example Plugin Agent is running!")
        
        # Access a required field from the state
        reqs = state.get("requirements") or ""
        
        # Produce the output
        output_data = f"Processed {len(reqs)} characters of requirements."
        
        # The agent should return a dictionary of state updates
        return {
            "example_output": output_data
        }
