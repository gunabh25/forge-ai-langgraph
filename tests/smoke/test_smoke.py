"""Pytest-based smoke tests for ForgeAI."""

import os
from app.settings import settings
from app.graph import compile_workflow

def test_environment_variables():
    """Verify essential environment variables are loaded."""
    assert settings.LLM_PROVIDER is not None
    assert settings.MODEL_NAME is not None

def test_graph_compiles():
    """Verify that the LangGraph StateGraph compiles without errors."""
    workflow = compile_workflow()
    assert workflow is not None
    
def test_artifact_directories():
    """Verify artifact directories are configured correctly."""
    assert settings.ARTIFACT_ROOT is not None
    assert isinstance(settings.ARTIFACT_ROOT, str)
    assert len(settings.ARTIFACT_ROOT) > 0
