"""Human approval gating interface and implementations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from core.constants import ApprovalStatuses

@dataclass
class ApprovalResult:
    """Dataclass holding human approval decision and related context feedback."""
    status: str  # Matches core.constants.ApprovalStatuses
    feedback: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ApprovalInterface(ABC):
    """Abstract interface class to query a human operator for validation approvals."""
    
    @abstractmethod
    def request_approval(self, stage: str, context: Dict[str, Any]) -> ApprovalResult:
        """Prompt a human user/system for approval for a given workflow stage.
        
        Args:
            stage: The workflow stage requiring gating (e.g. "solution_architecture").
            context: Accompanying information or proposed file modifications.
            
        Returns:
            ApprovalResult detailing whether it is approved, rejected, or needs changes.
        """
        pass

class CLIApproval(ApprovalInterface):
    """Command-line approval utility prompting human decisions in the shell."""
    
    def request_approval(self, stage: str, context: Dict[str, Any]) -> ApprovalResult:
        """Prompts approval decision in terminal.
        
        Args:
            stage: Target stage.
            context: Context containing target document text under keys like "details".
            
        Returns:
            ApprovalResult containing status choice.
        """
        print("\n" + "="*60)
        print(f"🚨 HUMAN APPROVAL REQUIRED FOR STAGE: {stage.upper()}")
        print("="*60)
        
        if "details" in context:
            print(f"\nDocument details:\n{context['details']}")
            
        print("\nAvailable Decisions:")
        print("1. [A]pprove - Proceed to the next workflow stage")
        print("2. [C]hanges Requested - Ask for revisions with input feedback")
        print("3. [R]eject - Flag as unacceptable and stop execution")
        
        while True:
            choice = input("\nEnter decision (A/C/R): ").strip().upper()
            if choice == "A":
                print("✅ Decision: Approved")
                return ApprovalResult(status=ApprovalStatuses.APPROVED)
            elif choice == "C":
                feedback = input("📝 Enter your revision request / feedback details: ").strip()
                return ApprovalResult(status=ApprovalStatuses.CHANGES_REQUESTED, feedback=feedback)
            elif choice == "R":
                feedback = input("❌ Enter reason for complete rejection: ").strip()
                return ApprovalResult(status=ApprovalStatuses.REJECTED, feedback=feedback)
            else:
                print("Invalid input. Please enter A, C, or R.")
