"""General utility functions and helpers for ForgeAI."""

import os
import re
from datetime import datetime, timezone
from typing import Optional

def generate_timestamp() -> str:
    """Generate an ISO-8601 UTC timestamp string.
    
    Returns:
        String containing ISO timestamp.
    """
    return datetime.now(timezone.utc).isoformat()

def ensure_directory(path: str) -> None:
    """Ensure that a directory exists, creating it if it does not.
    
    Args:
        path: The path of the directory.
    """
    os.makedirs(path, exist_ok=True)

def safe_write_file(path: str, content: str) -> None:
    """Write content to a file safely and atomically using a temporary file.
    
    Args:
        path: Target filepath.
        content: String content to write.
    """
    ensure_directory(os.path.dirname(path))
    temp_path = f"{path}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        # Atomic rename to prevent corrupting existing files
        os.replace(temp_path, path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e

def wrap_in_markdown_code_block(content: str, language: str = "") -> str:
    """Wrap a raw string content inside markdown code block syntax.
    
    Args:
        content: Code content.
        language: Code block programming language identifier.
        
    Returns:
        Formatted markdown code block string.
    """
    return f"```{language}\n{content}\n```"

def extract_markdown_code_block(markdown: str, language: Optional[str] = None) -> str:
    """Extract and return code block content from markdown.
    
    If language is provided, matches code blocks labeled with that language.
    Otherwise, matches the first code block found. Returns the original string 
    stripped if no code blocks match.
    
    Args:
        markdown: Full markdown content.
        language: Optional language specifier (e.g. "json", "python").
        
    Returns:
        Extracted content string.
    """
    if language:
        pattern = re.compile(rf"```(?:{language})\n(.*?)\n```", re.DOTALL)
    else:
        pattern = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)\n```", re.DOTALL)
        
    match = pattern.search(markdown)
    return match.group(1).strip() if match else markdown.strip()
