"""Main entry point for ForgeAI CLI."""

import sys
import json
from app.workflow import ForgeWorkflow

def main() -> None:
    """Main CLI entry point for executing the ForgeAI workflow."""
    print("==================================================")
    print("ForgeAI - Multi-Agent Software Engineering Platform")
    print("==================================================")
    
    try:
        user_request = input("\nEnter your software request:\n> ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        sys.exit(0)
        
    if not user_request:
        print("Error: Request cannot be empty.")
        sys.exit(1)
        
    print("\nInitializing workflow...")
    workflow = ForgeWorkflow()
    
    print("Executing Engineering Manager orchestration layer...")
    try:
        final_state = workflow.execute(user_request)
    except Exception as e:
        print(f"\n❌ Error executing workflow: {e}")
        sys.exit(1)
        
    print("\n==================================================")
    print("Workflow Execution Complete")
    print("==================================================")
    print(f"Current Stage: {final_state.get('current_stage')}")
    print(f"Approval Status: {final_state.get('approval_status')}")
    
    messages = final_state.get("messages", [])
    if messages:
        print("\n--- Engineering Manager Response ---")
        print(messages[-1].content)
        
    print("\n--- Metadata ---")
    print(json.dumps(final_state.get("metadata", {}), indent=2))
    print("==================================================")

if __name__ == "__main__":
    main()
