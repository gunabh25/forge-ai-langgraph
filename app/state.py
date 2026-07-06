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

def merge_generated_files(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    """Reducer function to merge generated workspace file registries in LangGraph.
    
    Keys are relative file paths (e.g. 'src/controllers/user.py') and values
    are the file source code strings. Right-side values overwrite left-side
    values for the same key, allowing retries to update individual files.
    
    Args:
        left: Existing generated files map.
        right: New or updated generated files.
        
    Returns:
        Merged file registry.
    """
    merged = (left or {}).copy()
    merged.update(right or {})
    return merged

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
    
    # Generated workspace: relative path → file source code
    generated_files: Annotated[Dict[str, str], merge_generated_files]
    
    # Validation pipeline scores (set by parallel validation agents)
    qa_score: Optional[int]
    security_score: Optional[int]
    review_score: Optional[int]
    
    # Quality engine outputs (set by validation_summary node)
    quality_weights: Optional[Dict[str, float]]
    overall_quality_score: Optional[int]
    deployment_status: Optional[str]
    validation_summary: Optional[str]
    quality_report: Optional[str]
    
    # Quality gate decision (set by quality_gate node)
    quality_gate_status: Optional[str]
    
    # Final Project Report and Metrics
    production_readiness_report: Optional[str]
    production_readiness_score: Optional[int]
    final_report: Optional[str]
    project_status: Optional[str]
    generated_artifacts_count: Optional[int]
    generated_files_count: Optional[int]
    workflow_execution_time: Optional[str]
    agents_executed: Optional[int]
    parallel_executions: Optional[int]
    approval_gates_completed: Optional[int]
    estimated_time_saved: Optional[str]
    
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

