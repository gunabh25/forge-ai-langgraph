"""Workflow router for determining LangGraph stage transitions."""

from typing import Dict, Any, List, Optional
from core.constants import WorkflowStages, ApprovalStatuses
from app.state import ForgeState
from config.logging import get_logger

logger = get_logger("workflow.router")

class WorkflowRouter:
    """Determines workflow state transitions and validates next steps."""
    
    @staticmethod
    def get_next_stage(state: ForgeState) -> str:
        """Determines the next stage based on the current state.
        
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
            return WorkflowStages.REQUIREMENT_ANALYSIS
            
        if current_stage == WorkflowStages.REQUIREMENT_ANALYSIS:
            return WorkflowStages.SOLUTION_ARCHITECTURE
            
        if current_stage == WorkflowStages.SOLUTION_ARCHITECTURE:
            return WorkflowStages.HUMAN_APPROVAL
            
        if current_stage == WorkflowStages.HUMAN_APPROVAL:
            approval_status = state.get("approval_status")
            if approval_status == ApprovalStatuses.APPROVED:
                return WorkflowStages.BACKEND_ENGINEERING
            elif approval_status == ApprovalStatuses.CHANGES_REQUESTED:
                return WorkflowStages.SOLUTION_ARCHITECTURE
            else:
                return "END"
                
        if current_stage == WorkflowStages.BACKEND_ENGINEERING:
            return WorkflowStages.AI_SOFTWARE_ENGINEERING

        if current_stage == WorkflowStages.AI_SOFTWARE_ENGINEERING:
            return "END"
            
        if current_stage == WorkflowStages.PRODUCTION_READINESS:
            return WorkflowStages.FINAL_REPORT_GENERATION
            
        if current_stage == WorkflowStages.FINAL_REPORT_GENERATION:
            return "END"
            
        # Catch-all: terminate if we reach an unknown stage
        return "END"
