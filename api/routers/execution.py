from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from api.schemas.models import ExecutionResponse, ReplayRequest
from api.dependencies.core import get_orchestration_service
from api.services.orchestration_service import OrchestrationService

router = APIRouter()

@router.get(
    "/execution/{execution_id}", 
    response_model=ExecutionResponse,
    summary="Get Execution State",
    description="Retrieve the complete execution state, telemetry, metrics, and generated artifacts for a specific workflow execution.",
    response_description="Detailed execution payload.",
    responses={
        200: {"description": "Execution state retrieved successfully."},
        404: {"description": "Execution ID not found."}
    }
)
async def get_execution(
    execution_id: str = Path(..., description="The unique ID of the execution", example="exec_abc123"),
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """Retrieve metadata about a specific workflow execution."""
    result = service.get_execution(execution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    return ExecutionResponse(**result)

@router.post(
    "/execution/{execution_id}/replay", 
    response_model=ExecutionResponse,
    summary="Replay Execution",
    description="Replays a previously run workflow from a specific stage (or from the beginning).",
    response_description="The new execution state resulting from the replay.",
    responses={
        200: {"description": "Execution replayed successfully."},
        404: {"description": "Execution ID or stage not found."},
        500: {"description": "Internal Server Error."}
    }
)
async def replay_execution(
    request: ReplayRequest,
    execution_id: str = Path(..., description="The unique ID of the execution to replay", example="exec_abc123"),
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

@router.get(
    "/artifacts/{execution_id}/{artifact_path:path}",
    summary="Download Generated Artifact",
    description="Downloads a specific generated artifact (SVG, PNG, PUML, JSON) from a given execution.",
    response_description="The binary or text content of the artifact file.",
    responses={
        200: {"description": "Artifact downloaded successfully."},
        404: {"description": "Artifact or Execution not found."}
    }
)
async def get_artifact(
    artifact_path: str = Path(..., description="The relative path to the artifact file", example="diagrams/component_diagram_v1.svg"),
    execution_id: str = Path(..., description="The unique ID of the execution", example="exec_abc123"),
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """Download a generated artifact from the execution."""
    resolved_path = service.get_artifact_path(execution_id, artifact_path)
    if not resolved_path:
        raise HTTPException(status_code=404, detail="Artifact not found or access denied")
        
    import os
    filename = os.path.basename(resolved_path)
    return FileResponse(resolved_path, filename=filename)
