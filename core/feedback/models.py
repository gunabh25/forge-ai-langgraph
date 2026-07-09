"""Data models for Feedback Manager."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from core.utils import generate_timestamp

@dataclass
class UserFeedbackEntry:
    """Represents a single feedback entry from the user."""
    feedback_id: str
    user_id: str
    project_id: str
    prompt: str
    architecture: Dict[str, Any]
    generated_uml: Dict[str, str]
    user_feedback: str  # The actual text feedback or correction provided
    reasoning: List[Dict[str, Any]]
    execution_metadata: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=generate_timestamp)
