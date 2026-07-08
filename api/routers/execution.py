from fastapi import APIRouter, Depends, HTTPException, Path
from api.schemas.models import ExecutionResponse
from api.dependencies.core import get_orchestration_service
from api.services.orchestration_service import OrchestrationService

router = APIRouter()

@router.get("/execution/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str = Path(..., description="The unique ID of the execution"),
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """Retrieve metadata about a specific workflow execution."""
    result = service.get_execution(execution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    return ExecutionResponse(**result)
