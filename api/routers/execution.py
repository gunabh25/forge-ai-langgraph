from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from api.schemas.models import ExecutionResponse, ReplayRequest
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

@router.post("/execution/{execution_id}/replay", response_model=ExecutionResponse)
async def replay_execution(
    request: ReplayRequest,
    execution_id: str = Path(..., description="The unique ID of the execution to replay"),
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """Replay an execution, optionally from a specific stage."""
    try:
        result = service.replay_execution(execution_id, request.start_stage)
        return ExecutionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to replay execution: {e}")

@router.get("/execution/{execution_id}/artifacts/{artifact_path:path}")
async def get_artifact(
    artifact_path: str,
    execution_id: str = Path(..., description="The unique ID of the execution"),
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """Download a generated artifact from the execution."""
    resolved_path = service.get_artifact_path(execution_id, artifact_path)
    if not resolved_path:
        raise HTTPException(status_code=404, detail="Artifact not found or access denied")
        
    import os
    filename = os.path.basename(resolved_path)
    return FileResponse(resolved_path, filename=filename)
