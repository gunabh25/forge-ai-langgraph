import os
from typing import Tuple

class Validator:
    """Validates generated source code files."""
    
    @staticmethod
    def validate(file_path: str, content: str) -> Tuple[bool, str]:
        """Validate the generated file content.
        
        Returns:
            (is_valid, error_message)
        """
        # Non-empty check
        if not content or not content.strip():
            return False, "File content is completely empty."
            
        # Reasonable length (e.g. at least 10 chars)
        if len(content.strip()) < 10:
            return False, "File content is suspiciously short (< 10 characters)."
            
        # Valid extension
        base_name = os.path.basename(file_path)
        _, ext = os.path.splitext(base_name)
        if not ext and base_name not in ["Dockerfile", "Makefile"]:
            return False, f"File path '{file_path}' is missing an extension."
            
        # Basic Python checks if it's a Python file
        if ext == ".py":
            # Just a rudimentary check: if it uses certain things, did they import?
            # E.g., if we see 'BaseModel', we expect 'pydantic' or similar, but this is fuzzy.
            # A simpler check: ensure it doesn't contain placeholders.
            if "TODO:" in content or "pass" in content and len(content) < 50:
                return False, "Code appears to contain stubs or TODOs instead of full implementations."
                
        # UTF-8 check is implicit since we are passing strings which are unicode in Python 3.
        
        return True, ""
