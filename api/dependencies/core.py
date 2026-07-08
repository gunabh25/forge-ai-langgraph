"""FastAPI dependencies."""

from api.services.orchestration_service import OrchestrationService

# Single global instance to maintain the in-memory execution store
_orchestration_service_instance = OrchestrationService()

def get_orchestration_service() -> OrchestrationService:
    """Dependency injection for the Orchestration Service."""
    return _orchestration_service_instance
