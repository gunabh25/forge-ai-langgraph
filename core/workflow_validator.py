"""Workflow validation engine for Demo mode."""

from typing import Dict, Any, List
from config.logging import get_logger

logger = get_logger("workflow_validator")

class WorkflowValidator:
    """Validates that a workflow executed completely and correctly."""
    
    @staticmethod
    def validate(state: Dict[str, Any]) -> bool:
        """Validates the final state of the workflow."""
        is_valid = True
        
        expected_keys = [
            "requirements",
            "architecture",
            "backend_blueprint",
            "implementation",
        ]
        
        print("\n==================================================")
        print("Workflow Validation Report")
        print("==================================================")
        
        for key in expected_keys:
            if not state.get(key):
                print(f"❌ Missing artifact state: {key}")
                is_valid = False
            else:
                print(f"✅ State verified: {key}")
                
        artifacts = state.get("artifacts", {})
        if not artifacts:
            print("❌ No artifacts generated.")
            is_valid = False
        else:
            print(f"✅ Artifacts generated: {sum(len(v) for v in artifacts.values())}")
            
        metrics = state.get("metadata", {})
        if not metrics:
            print("❌ Metrics not recorded.")
            is_valid = False
        else:
            print("✅ Metrics verified.")
            
        print("==================================================")
        return is_valid
