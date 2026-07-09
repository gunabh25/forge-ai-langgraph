from fastapi import APIRouter, Depends, HTTPException
from api.schemas.models import UpdateRequest, UpdateResponse
from api.dependencies.core import get_orchestration_service
from api.services.orchestration_service import OrchestrationService

router = APIRouter()

@router.post("/update", response_model=UpdateResponse)
async def update_architecture(
    request: UpdateRequest,
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """Modify previous software design via Impact Analysis."""
    try:
        result = service.update_architecture(
            prompt=request.prompt,
            execution_id=request.execution_id,
            user_id=request.user_id,
            session_id=request.session_id
        )
        return UpdateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error during update")
