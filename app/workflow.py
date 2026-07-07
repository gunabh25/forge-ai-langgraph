"""Workflow entry point for executing the ForgeAI StateGraph."""

from typing import Dict, Any, Optional
from app.graph import compile_workflow
from app.state import validate_forge_state, ForgeState
from config.logging import get_logger
from core.utils import generate_timestamp
from core.constants import ApprovalStatuses
from core.workflow_events import WorkflowEventManager, EventTypes
from core.cli import ForgeDashboard
from core.timeline import TimelineEngine
from core.metrics import MetricsTracker
from core.diagram_generator import DiagramGenerator

logger = get_logger("app.workflow")

class ForgeWorkflow:
    """Entry point for executing the ForgeAI multi-agent workflow."""
    
    def __init__(
        self,
        dashboard=None,
        approval_interface=None,
        quality_gate_interface=None
    ):
        self.dashboard = dashboard
        self.approval_interface = approval_interface
        self.quality_gate_interface = quality_gate_interface

        self.workflow = compile_workflow(
            dashboard=dashboard,
            approval_interface=approval_interface,
            quality_gate_interface=quality_gate_interface
        )
        
    def execute(self, user_request: str) -> Dict[str, Any]:
        """Initializes and runs the StateGraph."""

        # Create ONE dashboard instance
        dashboard = ForgeDashboard()

        # Save it
        self.dashboard = dashboard

        # Rebuild workflow with this dashboard
        self.workflow = compile_workflow(
            dashboard=dashboard,
            approval_interface=self.approval_interface,
            quality_gate_interface=self.quality_gate_interface,
        )

        logger.info(
            "Starting ForgeAI workflow...",
            extra={"user_request": user_request},
        )
        
        # Initialize the state
        initial_state: Dict[str, Any] = {
            "user_request": user_request,
            "current_stage": "",
            "approval_status": ApprovalStatuses.PENDING,
            "approval_history": [],
            "requirements": None,
            "architecture": None,
            "backend_blueprint": None,
            "implementation": None,
            "qa_report": None,
            "security_report": None,
            "review_report": None,
            "deployment_blueprint": None,
            "generated_files": {},
            "artifacts": {},
            "messages": [],
            "metadata": {
                "started_at": generate_timestamp(),
            }
        }
        
        # Validate state before execution
        logger.info("Validating initial state before execution...")
        validate_forge_state(initial_state, is_before_execution=True)
        
        # Initialize DX Engines
        event_manager = WorkflowEventManager()
        timeline_engine = TimelineEngine()
        dashboard = ForgeDashboard()
        
        # Run the graph inside the Live Dashboard context
        logger.info("Executing StateGraph...")
        event_manager.publish(EventTypes.WORKFLOW_STARTED, {"request": user_request})
        
        try:
            with dashboard.start():
                final_state = self.workflow.invoke(initial_state)
            
            event_manager.publish(EventTypes.WORKFLOW_COMPLETED, {"state": final_state})
        except Exception as e:
            event_manager.publish(EventTypes.WORKFLOW_FAILED, {"error": str(e), "state": initial_state})
            logger.error(f"Error during StateGraph execution: {e}", exc_info=True)
            raise e
            
        # Post-execution Generation (Metrics, Timeline, Diagrams)
        # pyrefly: ignore [bad-argument-type]
        MetricsTracker.generate_reasoning_artifact(final_state)
        # pyrefly: ignore [bad-argument-type]
        MetricsTracker.display_metrics(final_state)
        DiagramGenerator.generate_all()
        
        # Validate state after execution
        logger.info("Validating final state after execution...")
        validate_forge_state(final_state, is_before_execution=False)
        
        logger.info("Workflow finished")
        return final_state
