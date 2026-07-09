"""Data models for Conversation Memory."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from core.utils import generate_timestamp

@dataclass
class User:
    """Represents a unique user in the system."""
    user_id: str
    name: str
    created_at: str = field(default_factory=generate_timestamp)
    
@dataclass
class ConversationTurn:
    """Represents a single interaction turn."""
    turn_id: str
    prompt: str
    intent: Optional[Dict[str, Any]] = None
    execution_plan: Optional[List[str]] = None
    requirements_version: Optional[Dict[str, Any]] = None
    architecture_version: Optional[Dict[str, Any]] = None
    diagram_versions: Optional[Dict[str, str]] = None
    selected_uml_diagrams_version: Optional[List[Dict[str, Any]]] = None
    diagram_execution_states_version: Optional[Dict[str, Any]] = None
    artifacts: Dict[str, List[str]] = field(default_factory=dict)
    final_state_summary: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=generate_timestamp)

@dataclass
class Session:
    """Represents a conversation session for a user."""
    session_id: str
    user_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    created_at: str = field(default_factory=generate_timestamp)
