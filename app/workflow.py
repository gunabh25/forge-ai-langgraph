"""Workflow entry point for executing the ForgeAI StateGraph."""

from typing import Dict, Any
from app.graph import compile_workflow
from app.state import validate_forge_state, ForgeState
from config.logging import get_logger
from core.utils import generate_timestamp
from core.constants import ApprovalStatuses

logger = get_logger("app.workflow")

class ForgeWorkflow:
    """Entry point for executing the ForgeAI multi-agent workflow."""
    
    def __init__(self):
        self.workflow = compile_workflow()
        
    def execute(self, user_request: str) -> Dict[str, Any]:
        """Initializes and runs the StateGraph for a given user request.
        
        Args:
            user_request: The description of the software to build.
            
        Returns:
            The final state dict of the workflow.
        """
        logger.info("Starting ForgeAI workflow...", extra={"user_request": user_request})
        
        # Initialize the state
        initial_state: Dict[str, Any] = {
            "user_request": user_request,
            "current_stage": "",
            "approval_status": ApprovalStatuses.PENDING,
            "requirements": None,
            "architecture": None,
            "backend_blueprint": None,
            "implementation": None,
            "qa_report": None,
            "security_report": None,
            "review_report": None,
            "deployment_blueprint": None,
            "artifacts": {},
            "messages": [],
            "metadata": {
                "started_at": generate_timestamp(),
            }
        }
        
        # Validate state before execution
        logger.info("Validating initial state before execution...")
        validate_forge_state(initial_state, is_before_execution=True)
        
        # Run the graph
        logger.info("Executing StateGraph...")
        try:
            final_state = self.workflow.invoke(initial_state)
        except Exception as e:
            logger.error(f"Error during StateGraph execution: {e}", exc_info=True)
            raise e
            
        # Validate state after execution
        logger.info("Validating final state after execution...")
        validate_forge_state(final_state, is_before_execution=False)
        
        logger.info("ForgeAI workflow finished successfully.")
        return final_state
