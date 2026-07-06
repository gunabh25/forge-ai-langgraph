"""Demo entry point for executing the complete ForgeAI pipeline."""

import sys
from app.workflow import ForgeWorkflow
from core.approval import AutoApproval, AutoQualityGate
from core.workflow_validator import WorkflowValidator
from config.logging import get_logger

logger = get_logger("demo")

def run_demo():
    """Executes the ForgeAI Demo Workflow."""
    print("==================================================")
    print("ForgeAI - Demo Mode")
    print("==================================================")
    
    try:
        with open("examples/pos.md", "r") as f:
            user_request = f.read()
    except FileNotFoundError:
        print("❌ Error: examples/pos.md not found. Cannot run demo.")
        sys.exit(1)
        
    print("\nInitializing demo workflow with Auto-Approval mechanisms...\n")
    
    # Inject auto-approvals
    workflow = ForgeWorkflow(
        approval_interface=AutoApproval(),
        quality_gate_interface=AutoQualityGate()
    )
    
    try:
        final_state = workflow.execute(user_request)
    except Exception as e:
        logger.error(f"Demo Workflow Failed: {e}", exc_info=True)
        print(f"\n❌ Demo Workflow Failed: {e}")
        sys.exit(1)
        
    print("\n🎉 Demo Workflow Completed Successfully.")
    
    # Run Validator
    WorkflowValidator.validate(final_state)
    
if __name__ == "__main__":
    run_demo()
