from fastapi import APIRouter, Depends, HTTPException
from api.schemas.models import GenerateRequest, GenerateResponse
from api.dependencies.core import get_orchestration_service
from api.services.orchestration_service import OrchestrationService

router = APIRouter()

@router.post("/generate", response_model=GenerateResponse)
async def generate_architecture(
    request: GenerateRequest,
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """Generate software architecture and UML diagrams."""
    try:
        result = service.generate_architecture(
            prompt=request.prompt,
            diagram_types=request.diagram_types
        )
        return GenerateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error during generation")
