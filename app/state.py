"""State definitions for the LangGraph multi-agent workflow."""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from core.constants import ApprovalStatuses

def merge_artifacts(left: Dict[str, List[str]], right: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Reducer function to merge artifact version dictionaries in LangGraph.
    
    Combines two dictionaries mapping artifact stage names to lists of path strings,
    preserving unique values and keeping the lists ordered.
    
    Args:
        left: Existing artifact map.
        right: New artifact updates.
        
    Returns:
        Deduplicated, merged artifact map.
    """
    merged = left.copy() if left else {}
    for stage, paths in (right or {}).items():
        if stage in merged:
            # Deduplicate while preserving order of addition
            merged[stage] = list(dict.fromkeys(merged[stage] + paths))
        else:
            merged[stage] = paths
    return merged

def merge_metadata(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """Reducer function to merge workflow metadata dictionaries in LangGraph.
    
    Args:
        left: Existing metadata.
        right: Metadata updates.
        
    Returns:
        Merged metadata dictionary.
    """
    merged = left.copy() if left else {}
    if right:
        merged.update(right)
    return merged

class ForgeState(TypedDict):
    """Central shared state dictionary for the ForgeAI LangGraph workflow."""
    
    # Primary request and stage details
    user_request: str
    current_stage: str
    
    # Gating and status flags
    approval_status: str  # e.g., "pending", "approved", "rejected", "changes_requested"
    
    # Core stage outputs (Markdown content)
    requirements: Optional[str]
    architecture: Optional[str]
    backend_blueprint: Optional[str]
    implementation: Optional[str]
    qa_report: Optional[str]
    security_report: Optional[str]
    review_report: Optional[str]
    deployment_blueprint: Optional[str]
    
    # Reducer-managed tracking collections
    artifacts: Annotated[Dict[str, List[str]], merge_artifacts]
    messages: Annotated[List[BaseMessage], add_messages]
    metadata: Annotated[Dict[str, Any], merge_metadata]
