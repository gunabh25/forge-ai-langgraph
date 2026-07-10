"""Pydantic schemas for the ForgeAI FastAPI endpoints."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# Health Endpoints
# ---------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = Field(..., description="Current status of the API", json_schema_extra={'example': "healthy"})

# ---------------------------------------------------------
# Generate Endpoints
# ---------------------------------------------------------

class GenerateRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="Unique identifier for the user", json_schema_extra={'example': "user_123"})
    session_id: Optional[str] = Field(None, description="Session identifier for memory retention", json_schema_extra={'example': "session_456"})
    prompt: str = Field(..., min_length=5, description="The software architecture prompt to generate", json_schema_extra={'example': "Create a microservices e-commerce system."})
    diagram_types: Optional[List[str]] = Field(
        default=None, 
        description="Optional list of specific UML diagrams to generate (e.g. 'component', 'sequence')",
        json_schema_extra={'example': ["component", "sequence"]}
    )

class GenerateResponse(BaseModel):
    execution_id: str = Field(..., description="Unique ID for this generation execution", json_schema_extra={'example': "exec_abc123"})
    user_id: Optional[str] = Field(None, description="User identifier if provided", json_schema_extra={'example': "user_123"})
    requirements: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Generated software requirements")
    architecture: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Generated software architecture components")
    selected_diagrams: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Metadata of selected diagrams")
    plantuml: Optional[Dict[str, str]] = Field(default_factory=dict, description="Raw PlantUML source code for generated diagrams")
    validation_reports: Optional[Dict[str, Any]] = Field(default_factory=dict, description="PlantUML syntax validation and compiler reports")
    rendered_artifacts: Optional[Dict[str, str]] = Field(default_factory=dict, description="References to the rendered SVG/PNG artifacts")
    execution_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Execution telemetry and analytics")
    execution_metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Performance and latency metrics")
    artifacts: Optional[Dict[str, Any]] = Field(default_factory=dict, description="All artifacts generated during workflow")

# ---------------------------------------------------------
# Update Endpoints
# ---------------------------------------------------------

class UpdateRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="Unique identifier for the user", json_schema_extra={'example': "user_123"})
    session_id: Optional[str] = Field(None, description="Session identifier for memory retention", json_schema_extra={'example': "session_456"})
    prompt: str = Field(..., min_length=5, description="The prompt describing what to update in the architecture", json_schema_extra={'example': "Add Redis caching to the data layer."})
    execution_id: Optional[str] = Field(None, description="The ID of the previous execution to update (for incremental generation)", json_schema_extra={'example': "exec_abc123"})

class UpdateResponse(BaseModel):
    execution_id: str = Field(..., description="Unique ID for this update execution", json_schema_extra={'example': "exec_def456"})
    affected_diagrams: List[str] = Field(default_factory=list, description="List of diagram types that were updated")
    reused_diagrams: List[str] = Field(default_factory=list, description="List of diagram types that were reused from cache")
    updated_artifacts: Dict[str, str] = Field(default_factory=dict, description="References to the newly updated artifacts")
    execution_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Execution telemetry and analytics")
    artifacts: Optional[Dict[str, Any]] = Field(default_factory=dict, description="All artifacts available after update")
    validation_reports: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Validation reports for the updated generation")
    execution_metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Performance and latency metrics")

# ---------------------------------------------------------
# Feedback Endpoints
# ---------------------------------------------------------

class FeedbackRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="Unique identifier for the user", json_schema_extra={'example': "user_123"})
    execution_id: str = Field(..., description="Execution ID this feedback applies to", json_schema_extra={'example': "exec_abc123"})
    feedback: str = Field(..., min_length=2, description="The feedback content", json_schema_extra={'example': "Component diagram should separate Parser and Compliance Engine."})

class FeedbackResponse(BaseModel):
    status: str = Field(..., description="Status of the feedback submission", json_schema_extra={'example': "stored"})
    art_plugin: str = Field(..., description="ART Plugin processing status", json_schema_extra={'example': "processed"})
    execution_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Feedback execution telemetry")
    artifacts: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Artifact references if applicable")
    validation_reports: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Validation logs")
    execution_metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metrics related to feedback processing")

# ---------------------------------------------------------
# Execution Endpoints
# ---------------------------------------------------------

class ExecutionResponse(BaseModel):
    execution_id: str = Field(..., description="The unique execution ID", json_schema_extra={'example': "exec_abc123"})
    agents_executed: List[str] = Field(default_factory=list, description="List of agents that ran during this execution")
    llm_calls: int = Field(0, description="Total number of LLM calls made")
    execution_time_ms: int = Field(0, description="Total end-to-end latency in milliseconds")
    validation_retries: int = Field(0, description="Number of times diagrams failed validation and were retried")
    artifacts_generated: Dict[str, Any] = Field(default_factory=dict, description="Map of generated artifacts")
    
    execution_graph: Optional[List[str]] = Field(default=None, description="The dynamic execution plan graph.", json_schema_extra={'example': ["IntentAnalyzer", "UMLGenerator"]})
    execution_timeline: Optional[List[Dict[str, Any]]] = Field(default=None, description="Timeline of execution events.")
    reasoning: Optional[List[Dict[str, Any]]] = Field(default=None, description="Agent reasoning logs.")
    generated_diagrams: Optional[Dict[str, Any]] = Field(default=None, description="PlantUML and rendered diagram paths.")
    validation_reports: Optional[Dict[str, Any]] = Field(default_factory=dict, description="QA, Security, and Review reports.")
    rendered_artifacts: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Paths to rendered workspace artifacts.")
    execution_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Raw execution metrics and state history")
    artifacts: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Unified artifacts map")
    execution_metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metrics specific to this execution")

class ReplayRequest(BaseModel):
    start_stage: Optional[str] = Field(default=None, description="Optional stage to restart the replay from.", json_schema_extra={'example': "UMLGenerator"})

# ---------------------------------------------------------
# Monitoring Endpoints
# ---------------------------------------------------------

class MetricsResponse(BaseModel):
    total_executions: int = Field(0, description="Total number of completed workflows", json_schema_extra={'example': 42})
    successful_executions: int = Field(0, description="Total number of successful workflows", json_schema_extra={'example': 40})
    failed_executions: int = Field(0, description="Total number of failed workflows", json_schema_extra={'example': 2})
    average_latency_ms: float = Field(0.0, description="Average workflow execution latency in milliseconds", json_schema_extra={'example': 12450.5})
    total_llm_calls: int = Field(0, description="Total cumulative LLM calls made across all workflows", json_schema_extra={'example': 350})
    diagrams_rendered: int = Field(0, description="Total number of PlantUML diagrams successfully rendered", json_schema_extra={'example': 120})
