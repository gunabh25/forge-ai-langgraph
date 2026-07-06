"""Human approval gating interface and implementations."""

import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from core.constants import ApprovalStatuses
from config.logging import get_logger

logger = get_logger("core.approval")

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

def parse_architecture_summary(architecture_text: str) -> Dict[str, str]:
    """Extract key architectural details from the Architecture Specification markdown."""
    summary = {
        "pattern": "N/A",
        "database": "N/A",
        "authentication": "N/A",
        "apis": "N/A",
        "scalability": "N/A"
    }
    if not architecture_text:
        return summary
        
    # 1. Parse Architecture Pattern
    pattern_match = re.search(r"(?:^|\n)#+\s*Architecture Pattern\s*\n(.*?)(?=\n#+|$)", architecture_text, re.DOTALL | re.IGNORECASE)
    if pattern_match:
        lines = [line.strip() for line in pattern_match.group(1).split("\n") if line.strip()]
        if lines:
            summary["pattern"] = lines[0].lstrip("-* ").strip()
            
    # 2. Parse Technology Stack details (Database, Authentication)
    tech_match = re.search(r"(?:^|\n)#+\s*Technology Stack\s*\n(.*?)(?=\n#+|$)", architecture_text, re.DOTALL | re.IGNORECASE)
    if tech_match:
        tech_content = tech_match.group(1)
        db_line = re.search(r"-\s*\*\*Database\*\*:\s*(.*)", tech_content, re.IGNORECASE)
        if db_line:
            summary["database"] = db_line.group(1).strip()
        auth_line = re.search(r"-\s*\*\*Authentication\*\*:\s*(.*)", tech_content, re.IGNORECASE)
        if auth_line:
            summary["authentication"] = auth_line.group(1).strip()
            
    # 3. Parse API Design
    api_match = re.search(r"(?:^|\n)#+\s*API Design\s*\n(.*?)(?=\n#+|$)", architecture_text, re.DOTALL | re.IGNORECASE)
    if api_match:
        lines = [line.strip() for line in api_match.group(1).split("\n") if line.strip()]
        # Clean list formatting and take first 2
        cleaned_apis = [l.lstrip("-* ").strip() for l in lines if l.strip() and not l.startswith("- **")][:2]
        summary["apis"] = ", ".join(cleaned_apis) if cleaned_apis else "N/A"
        
    # 4. Parse Scalability
    scale_match = re.search(r"(?:^|\n)#+\s*Scalability Strategy\s*\n(.*?)(?=\n#+|$)", architecture_text, re.DOTALL | re.IGNORECASE)
    if scale_match:
        lines = [line.strip() for line in scale_match.group(1).split("\n") if line.strip()]
        cleaned_scale = [l.lstrip("-* ").strip() for l in lines if l.strip() and not l.startswith("- **")][:2]
        summary["scalability"] = ", ".join(cleaned_scale) if cleaned_scale else "N/A"
        
    return summary

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
        # Load details
        architecture_text = context.get("architecture", "")
        summary = parse_architecture_summary(architecture_text)
        
        print("\n==================================")
        print("\nArchitecture Review")
        print("\nStatus:")
        print("Ready for Approval")
        print("\nGenerated Documents")
        print("✓ Requirements Specification")
        print("✓ Architecture Specification")
        print("\nSummary")
        print(f"• Architecture Pattern: {summary['pattern']}")
        print(f"• Database: {summary['database']}")
        print(f"• Authentication: {summary['authentication']}")
        print(f"• APIs: {summary['apis']}")
        print(f"• Scalability: {summary['scalability']}")
        print("\nChoose")
        print("1 Approve")
        print("2 Request Changes")
        print("3 Reject")
        print("\n==================================")
        
        logger.info("Approval requested")
        
        while True:
            try:
                choice = input("\nEnter choice (1-3): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nAborted.")
                return ApprovalResult(status=ApprovalStatuses.REJECTED, feedback="CLI input interrupted")
                
            if choice == "1":
                logger.info("Approval received")
                return ApprovalResult(status=ApprovalStatuses.APPROVED)
            elif choice == "2":
                try:
                    feedback = input("📝 Enter your revision request / feedback details: ").strip()
                except (KeyboardInterrupt, EOFError):
                    feedback = "Changes requested via CLI abort"
                logger.info("Approval received")
                return ApprovalResult(status=ApprovalStatuses.CHANGES_REQUESTED, feedback=feedback)
            elif choice == "3":
                try:
                    feedback = input("❌ Enter reason for complete rejection: ").strip()
                except (KeyboardInterrupt, EOFError):
                    feedback = "Rejected via CLI abort"
                logger.info("Approval received")
                return ApprovalResult(status=ApprovalStatuses.REJECTED, feedback=feedback)
            else:
                print("Invalid input. Please enter 1, 2, or 3.")
