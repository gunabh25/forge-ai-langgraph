from fastapi import APIRouter, Depends
from api.schemas.models import MetricsResponse
from api.dependencies.core import get_orchestration_service
from api.services.orchestration_service import OrchestrationService

router = APIRouter()

@router.get(
    "/metrics", 
    response_model=MetricsResponse,
    summary="Get System Metrics",
    description="Retrieves high-level performance and execution metrics across all workflows.",
    response_description="A summary of system execution metrics."
)
async def get_metrics(
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """Retrieve global system metrics."""
    result = service.get_metrics()
    return MetricsResponse(**result)
