"""State definitions for the LangGraph multi-agent workflow."""

from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
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

def merge_approval_history(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reducer function to merge approval history logs in LangGraph."""
    return (left or []) + (right or [])

class ForgeState(TypedDict):
    """Central shared state dictionary for the ForgeAI LangGraph workflow."""
    
    # Primary request and stage details
    user_request: str
    current_stage: str
    
    # Gating and status flags
    approval_status: str  # e.g., "pending", "approved", "rejected", "changes_requested"
    approval_history: Annotated[List[Dict[str, Any]], merge_approval_history]
    
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

def validate_forge_state(state: Dict[str, Any], is_before_execution: bool = True) -> None:
    """Validates the structure and content of ForgeState.
    
    Args:
        state: State dictionary to validate.
        is_before_execution: True if validating before running the graph, False if after.
        
    Raises:
        ValueError: If validation fails.
    """
    if not isinstance(state, dict):
        raise ValueError("ForgeState must be a dictionary.")
        
    # Check user_request
    user_request = state.get("user_request")
    if user_request is None:
        raise ValueError("ForgeState validation failed: 'user_request' is missing.")
    if not isinstance(user_request, str) or not user_request.strip():
        raise ValueError("ForgeState validation failed: 'user_request' must be a non-empty string.")
        
    if not is_before_execution:
        # Check current_stage
        current_stage = state.get("current_stage")
        if not current_stage:
            raise ValueError("ForgeState validation failed: 'current_stage' must be set after execution.")
            
        # Check approval_status
        approval_status = state.get("approval_status")
        if not approval_status:
            raise ValueError("ForgeState validation failed: 'approval_status' must be set after execution.")
            
        # Check messages
        messages = state.get("messages")
        if messages is None:
            raise ValueError("ForgeState validation failed: 'messages' list is missing.")
        if not isinstance(messages, list) or len(messages) == 0:
            raise ValueError("ForgeState validation failed: 'messages' must contain at least the orchestrator's analysis.")

