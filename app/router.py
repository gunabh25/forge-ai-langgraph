"""Workflow router for determining LangGraph stage transitions."""

from typing import Dict, Any, List, Optional
from core.constants import WorkflowStages
from app.state import ForgeState
from config.logging import get_logger

logger = get_logger("workflow.router")

class WorkflowRouter:
    """Determines workflow state transitions and validates next steps."""
    
    @staticmethod
    def get_next_stage(state: ForgeState) -> str:
        """Determines the next stage based on the current state.
        
        For Milestone 3:
        Initially supports: ENGINEERING_MANAGEMENT -> END.
        Designed for future expansion to route through the standard SDLC path.
        
        Args:
            state: The current ForgeState.
            
        Returns:
            The name of the next stage or 'END' to terminate.
        """
        current_stage = state.get("current_stage")
        logger.info(f"Routing logic invoked. Current stage: {current_stage}", extra={"current_stage": current_stage})
        
        if not current_stage:
            return WorkflowStages.ENGINEERING_MANAGEMENT
            
        if current_stage == WorkflowStages.ENGINEERING_MANAGEMENT:
            # In future milestones, this will route to WorkflowStages.REQUIREMENT_ANALYSIS.
            # For Milestone 3, we terminate immediately.
            return "END"
            
        # Catch-all: terminate if we reach an unknown stage
        return "END"
