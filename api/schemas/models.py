"""Pydantic schemas for the ForgeAI FastAPI endpoints."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# Health Endpoints
# ---------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={'example': "healthy"})

# ---------------------------------------------------------
# Generate Endpoints
# ---------------------------------------------------------

class GenerateRequest(BaseModel):
    user_id: Optional[str] = Field(None, json_schema_extra={'example': "user_123"})
    session_id: Optional[str] = Field(None, json_schema_extra={'example': "session_456"})
    prompt: str = Field(..., json_schema_extra={'example': "Create a microservices e-commerce system."})
    diagram_types: Optional[List[str]] = Field(
        default=None, 
        json_schema_extra={'example': ["component", "sequence"]}
    )

class GenerateResponse(BaseModel):
    execution_id: str
    user_id: Optional[str] = None
    requirements: Optional[Dict[str, Any]] = None
    architecture: Optional[Dict[str, Any]] = None
    selected_diagrams: Optional[List[Dict[str, Any]]] = None
    plantuml: Optional[Dict[str, str]] = None
    validation: Optional[Dict[str, Any]] = None
    rendered_artifacts: Optional[Dict[str, str]] = None
    execution_metadata: Optional[Dict[str, Any]] = None

# ---------------------------------------------------------
# Update Endpoints
# ---------------------------------------------------------

class UpdateRequest(BaseModel):
    user_id: Optional[str] = Field(None, json_schema_extra={'example': "user_123"})
    session_id: Optional[str] = Field(None, json_schema_extra={'example': "session_456"})
    prompt: str = Field(..., json_schema_extra={'example': "Add Redis caching."})
    execution_id: Optional[str] = Field(None, description="The ID of the previous execution to update")

class UpdateResponse(BaseModel):
    affected_diagrams: List[str] = Field(default_factory=list)
    reused_diagrams: List[str] = Field(default_factory=list)
    updated_artifacts: Dict[str, str] = Field(default_factory=dict)

# ---------------------------------------------------------
# Feedback Endpoints
# ---------------------------------------------------------

class FeedbackRequest(BaseModel):
    user_id: Optional[str] = Field(None, json_schema_extra={'example': "user_123"})
    execution_id: str = Field(..., json_schema_extra={'example': "exec_abc123"})
    feedback: str = Field(..., json_schema_extra={'example': "Component diagram should separate Parser and Compliance Engine."})

class FeedbackResponse(BaseModel):
    status: str = Field(..., json_schema_extra={'example': "stored"})
    art_plugin: str = Field(..., json_schema_extra={'example': "processed"})

# ---------------------------------------------------------
# Execution Endpoints
# ---------------------------------------------------------

class ExecutionResponse(BaseModel):
    execution_id: str
    agents_executed: List[str] = Field(default_factory=list)
    llm_calls: int = 0
    execution_time_ms: int = 0
    validation_retries: int = 0
    artifacts_generated: Dict[str, Any] = Field(default_factory=dict)
    
    # New Observability Fields
    execution_graph: Optional[List[str]] = Field(default=None, description="The dynamic execution plan graph.")
    execution_timeline: Optional[List[Dict[str, Any]]] = Field(default=None, description="Timeline of execution events.")
    reasoning: Optional[List[Dict[str, Any]]] = Field(default=None, description="Agent reasoning logs.")
    generated_diagrams: Optional[Dict[str, Any]] = Field(default=None, description="PlantUML and rendered diagram paths.")
    validation_reports: Optional[Dict[str, Any]] = Field(default=None, description="QA, Security, and Review reports.")
    rendered_artifacts: Optional[Dict[str, Any]] = Field(default=None, description="Paths to rendered workspace artifacts.")

class ReplayRequest(BaseModel):
    start_stage: Optional[str] = Field(default=None, description="Optional stage to restart the replay from.")
