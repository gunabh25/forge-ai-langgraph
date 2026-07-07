import json
import re
from typing import Dict, Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from config.logging import get_logger
from core.llm import get_llm
from core.prompts import load_prompt

logger = get_logger("agents.ai_software_engineer.manifest_generator")

class ManifestGenerator:
    """Generates the project scope and manifest of files to generate."""
    
    _FENCE_PATTERN = re.compile(
        r"^\s*```(?:json)?\s*\n(.*?)\n\s*```\s*$",
        re.DOTALL,
    )

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self.llm = llm or get_llm()
        import os
        prompt_path = os.path.join(os.path.dirname(__file__), "manifest_prompt.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
        
    def generate(self, requirements: str, architecture: str, backend_blueprint: str) -> Dict[str, Any]:
        """Generate the project manifest."""
        logger.info("Generating project manifest...")
        
        human_content = (
            f"Requirements Specification:\n{requirements}\n\n"
            f"Architecture Specification:\n{architecture}\n\n"
            f"Backend Blueprint:\n{backend_blueprint}"
        )
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=human_content),
        ]
        
        response = self.llm.invoke(messages)
        raw_content = str(response.content)
        
        # Strip markdown fence if present
        fence_match = self._FENCE_PATTERN.match(raw_content.strip())
        if fence_match:
            raw_content = fence_match.group(1).strip()
            
        # Try to locate the JSON object
        start = raw_content.find("{")
        end = raw_content.rfind("}")
        if start != -1 and end != -1 and end >= start:
            raw_content = raw_content[start : end + 1]
            
        try:
            manifest = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse manifest JSON: {exc}. Response preview: {raw_content[:300]!r}") from exc
            
        if not isinstance(manifest, dict):
            raise ValueError("Expected a JSON object for the manifest.")
            
        if "files" not in manifest or not isinstance(manifest["files"], list):
            raise ValueError("Manifest must contain a 'files' list.")
            
        logger.info(f"Manifest generated successfully with {len(manifest['files'])} files.")
        return manifest
