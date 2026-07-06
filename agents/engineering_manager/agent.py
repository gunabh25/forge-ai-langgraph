"""Engineering Manager Agent implementation."""

from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from core.llm import get_llm
from core.prompts import load_prompt, load_examples
from app.state import ForgeState
from config.logging import get_logger
from core.constants import WorkflowStages, ApprovalStatuses
from core.utils import generate_timestamp

logger = get_logger("agents.engineering_manager")

class EngineeringManagerAgent:
    """Engineering Manager agent responsible for orchestrating the multi-agent workflow."""
    
    def __init__(self):
        self.llm = get_llm()
        self.system_prompt = load_prompt("engineering_manager")
        try:
            self.examples = load_examples("engineering_manager")
        except FileNotFoundError:
            self.examples = ""
            
    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Engineering Manager agent step.
        
        Args:
            state: The current shared ForgeState.
            
        Returns:
            Dictionary of state updates.
        """
        user_request = state.get("user_request", "").strip()
        logger.info("Engineering Manager starting execution...", extra={"user_request": user_request})
        
        if not user_request:
            raise ValueError("State validation failed: user_request is empty.")
            
        # Construct messages for the LLM
        prompt_content = self.system_prompt
        if self.examples:
            prompt_content += f"\n\nHere are some examples of how to coordinate the workflow:\n{self.examples}"
            
        messages = [
            SystemMessage(content=prompt_content),
            HumanMessage(content=f"User request: {user_request}")
        ]
        
        # Invoke the LLM
        logger.info("Invoking LLM for Engineering Manager analysis...")
        llm_response = self.llm.invoke(messages)
        
        # Coerce content to string safely
        response_content = llm_response.content
        if isinstance(response_content, list):
            response_content = "\n".join([str(item) for item in response_content])
        else:
            response_content = str(response_content)
            
        logger.info("LLM invocation completed.")
        
        # Build the state updates
        new_message = AIMessage(
            content=response_content,
            name="engineering_manager"
        )
        
        # Update metadata to track execution progress
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "engineering_manager_analysis_completed": True,
            "last_updated": generate_timestamp()
        }
        
        state_updates = {
            "current_stage": WorkflowStages.ENGINEERING_MANAGEMENT,
            "approval_status": ApprovalStatuses.PENDING,
            "messages": [new_message],
            "metadata": updated_metadata
        }
        
        logger.info("Engineering Manager execution complete. Returning state updates.", extra=state_updates)
        return state_updates
