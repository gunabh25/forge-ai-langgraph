from fastapi import APIRouter, Depends, HTTPException
from api.schemas.models import FeedbackRequest, FeedbackResponse
from api.dependencies.core import get_orchestration_service
from api.services.orchestration_service import OrchestrationService

router = APIRouter()

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """Submit feedback for Active Reinforcement Tuning."""
    try:
        result = service.submit_feedback(
            execution_id=request.execution_id,
            feedback=request.feedback,
            user_id=request.user_id or "api_user"
        )
        return FeedbackResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error processing feedback")
