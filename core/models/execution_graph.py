"""Strongly typed framework-independent graph representations."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ExecutionNode(BaseModel):
    """Represents a single executable node (agent) in the graph."""
    agent_name: str
    requires: List[str] = Field(default_factory=list)
    produces: List[str] = Field(default_factory=list)
    parallelizable: bool = False
    retryable: bool = False
    timeout: int = 300
    estimated_cost: float = 0.0
    estimated_latency: int = 0

class ExecutionEdge(BaseModel):
    """Represents a directed transition between two nodes."""
    source: str
    target: str
    condition: Optional[str] = None  # e.g., "retry", "continue"

class ExecutionGraph(BaseModel):
    """The complete framework-independent workflow execution graph."""
    nodes: Dict[str, ExecutionNode] = Field(default_factory=dict)
    edges: List[ExecutionEdge] = Field(default_factory=list)
    entry_node: Optional[str] = None
    exit_node: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CompilationError(Exception):
    """Structured diagnostic error for graph compilation failures."""
    
    def __init__(self, error: str, nodes: List[str], resolution: str):
        super().__init__(f"{error}: {nodes}. Resolution: {resolution}")
        self.error = error
        self.nodes = nodes
        self.resolution = resolution
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to structured diagnostic payload."""
        return {
            "error": self.error,
            "nodes": self.nodes,
            "resolution": self.resolution
        }
