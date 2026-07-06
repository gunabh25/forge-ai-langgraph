"""Unit tests for the prompt loader utilities."""

import os
import pytest
from core.prompts import load_prompt, load_examples, clear_prompt_cache

def test_load_prompt_missing_agent():
    """Verify FileNotFoundError is raised when target agent directory does not exist."""
    with pytest.raises(FileNotFoundError):
        load_prompt("non_existent_agent")

def test_load_prompt_and_examples(tmp_path, monkeypatch):
    """Verify loading from existing agent directories and cache hit mechanics."""
    # Create mock agent directory structure
    agent_dir = tmp_path / "mock_agent"
    agent_dir.mkdir()
    
    prompt_file = agent_dir / "prompt.md"
    prompt_file.write_text("# Mock System Prompt\nHello Agent")
    
    examples_file = agent_dir / "examples.md"
    examples_file.write_text("# Mock Examples\nExample 1")
    
    # Mock core.prompts.AGENT_DIR using monkeypatch
    monkeypatch.setattr("core.prompts.AGENT_DIR", str(tmp_path))
    
    # Clear cache before running just to ensure clean state
    clear_prompt_cache()
    
    # Read prompt and verify content
    content = load_prompt("mock_agent")
    assert content == "# Mock System Prompt\nHello Agent"
    
    # Read examples and verify content
    examples_content = load_examples("mock_agent")
    assert examples_content == "# Mock Examples\nExample 1"
    
    # Modify prompt file on disk directly
    prompt_file.write_text("# Mock System Prompt\nModified Hello Agent")
    
    # Re-reading should yield the cached content (not the modified disk content)
    cached_content = load_prompt("mock_agent")
    assert cached_content == "# Mock System Prompt\nHello Agent"
    
    # Clear cache
    clear_prompt_cache()
    
    # Re-reading should load the newly modified text from disk
    refreshed_content = load_prompt("mock_agent")
    assert refreshed_content == "# Mock System Prompt\nModified Hello Agent"
