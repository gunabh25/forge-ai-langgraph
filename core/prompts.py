"""Module for loading and caching agent prompts and examples."""

import os
from functools import lru_cache

# Find the agents directory relative to this file's location
AGENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../agents"))

@lru_cache(maxsize=32)
def load_prompt(agent_name: str) -> str:
    """Load the prompt.md file for a specific agent.
    
    Args:
        agent_name: The directory name of the agent under agents/.
        
    Returns:
        The content of the prompt.md file.
        
    Raises:
        FileNotFoundError: If the agent folder or prompt.md does not exist.
    """
    path = os.path.join(AGENT_DIR, agent_name, "prompt.md")
    if not os.path.exists(path):
        raise FileNotFoundError(f"System prompt file not found for agent '{agent_name}' at path: {path}")
        
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

@lru_cache(maxsize=32)
def load_examples(agent_name: str) -> str:
    """Load the examples.md file for a specific agent.
    
    Args:
        agent_name: The directory name of the agent under agents/.
        
    Returns:
        The content of the examples.md file.
        
    Raises:
        FileNotFoundError: If the agent folder or examples.md does not exist.
    """
    path = os.path.join(AGENT_DIR, agent_name, "examples.md")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Examples file not found for agent '{agent_name}' at path: {path}")
        
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def clear_prompt_cache() -> None:
    """Clear prompt and example loading caches."""
    load_prompt.cache_clear()
    load_examples.cache_clear()
