"""Main entry point for ForgeAI FastAPI Server."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config.logging import get_logger

from api.routers import generate, update, feedback, execution, health

logger = get_logger("api.main")

app = FastAPI(
    title="ForgeAI API",
    description="REST API for the ForgeAI Engineering Platform",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(generate.router, prefix="/api/v1", tags=["Generate"])
app.include_router(update.router, prefix="/api/v1", tags=["Update"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
app.include_router(execution.router, prefix="/api/v1", tags=["Execution"])
