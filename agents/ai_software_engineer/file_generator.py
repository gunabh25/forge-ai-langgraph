import re
import json
from typing import Dict, Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from config.logging import get_logger
from core.llm import get_llm
from core.prompts import load_prompt

logger = get_logger("agents.ai_software_engineer.file_generator")

class FileGenerator:
    """Generates a single source code file based on project context."""
    
    _FENCE_PATTERN = re.compile(
        r"^\s*```[a-zA-Z0-9_-]*\s*\n(.*)\n\s*```\s*$",
        re.DOTALL,
    )

    def __init__(self, llm: BaseChatModel = None):
        self.llm = llm or get_llm()
        import os
        prompt_path = os.path.join(os.path.dirname(__file__), "file_prompt.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
        
    def generate(
        self,
        file_path: str,
        requirements: str,
        architecture: str,
        backend_blueprint: str,
        manifest: Dict[str, Any],
        feedback: Optional[str] = None,
        previously_generated: Optional[Dict[str, str]] = None
    ) -> str:
        """Generate the content of a single file."""
        logger.info(f"Generating file: {file_path}")
        
        context_str = (
            f"Requirements Specification:\n{requirements}\n\n"
            f"Architecture Specification:\n{architecture}\n\n"
            f"Backend Blueprint:\n{backend_blueprint}\n\n"
            f"Project Manifest Scope:\n{json.dumps(manifest, indent=2)}\n\n"
        )
        
        if previously_generated:
            # We limit to files that were already generated to give context
            # We only show the names or limited contents if it's too big,
            # but for now, passing all previously generated files.
            # To avoid prompt bloat, we just list the paths of what was generated, 
            # and perhaps minimal content if needed. But for simplicity:
            context_str += "Previously Generated Files:\n"
            for p, content in previously_generated.items():
                context_str += f"--- {p} ---\n{content}\n\n"
        
        human_content = f"{context_str}\n\nGenerate ONLY the exact source code for: {file_path}"
        if feedback:
            human_content += f"\n\nValidation Feedback from previous attempt (Fix these issues):\n{feedback}"
            
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=human_content),
        ]
        
        response = self.llm.invoke(messages)
        raw_content = str(response.content)
        
        # Strip markdown fence if LLM wrapped the output
        fence_match = self._FENCE_PATTERN.match(raw_content.strip())
        if fence_match:
            raw_content = fence_match.group(1).strip()
            
        return raw_content
