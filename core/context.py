"""Context variables for observability and telemetry tracking."""

import contextvars
from typing import Optional

# Workflow tracking
workflow_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("workflow_id", default=None)
execution_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("execution_id", default=None)
session_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("session_id", default=None)
user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)

# Agent and Component tracking
current_agent_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_agent", default=None)
current_diagram_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_diagram", default=None)

# Execution details
retry_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("retry_id", default=None)
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)

# Provider details
provider_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("provider", default=None)
model_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("model", default=None)

def get_telemetry_context() -> dict:
    """Extract all current telemetry context variables into a dictionary."""
    ctx = {
        "workflow_id": workflow_id_var.get(),
        "execution_id": execution_id_var.get(),
        "session_id": session_id_var.get(),
        "user_id": user_id_var.get(),
        "agent": current_agent_var.get(),
        "diagram": current_diagram_var.get(),
        "retry_id": retry_id_var.get(),
        "request_id": request_id_var.get(),
        "provider": provider_var.get(),
        "model": model_var.get(),
    }
    return {k: v for k, v in ctx.items() if v is not None}
