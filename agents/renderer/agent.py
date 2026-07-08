"""Renderer Agent implementation."""

import json
from typing import Dict, Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from agents.base import BaseAgent
from core.agent_registry import AgentRegistry
from app.state import ForgeState
from config.logging import get_logger
from core.utils import generate_timestamp
from core.artifact_manager import ArtifactManager
from core.constants import ArtifactFolders

logger = get_logger("agents.renderer")

class RendererAgent(BaseAgent):
    """Renderer Agent responsible for mock conversion of PlantUML to SVG."""
    
    @property
    def name(self) -> str:
        return "Renderer Agent"
        
    @property
    def description(self) -> str:
        return "Converts validated PlantUML texts into SVG wrappers."
        
    @property
    def capabilities(self) -> List[str]:
        return ["plantuml_rendering", "svg_generation"]

    @property
    def requires(self) -> List[str]:
        return ["plantuml_validation_report"]

    @property
    def produces(self) -> List[str]:
        return ["rendered_svg_references"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        self.artifact_manager = ArtifactManager()

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Renderer Agent."""
        logger.info("Renderer Agent starting execution.")
        
        plantuml_diagrams = state.get("plantuml_diagrams", {})
        if not plantuml_diagrams:
            logger.warning("No PlantUML diagrams found to render.")
            return {}

        rendered_svg_references = {}
        svg_metadata = []
        artifacts_paths = []
        
        for diagram_name, puml_content in plantuml_diagrams.items():
            # Create a mock SVG that simply wraps the PlantUML syntax 
            # (In production, this would call a PlantUML jar or API)
            mock_svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg">
  <desc>Mock SVG for {diagram_name}</desc>
  <!-- PlantUML Source:
{puml_content}
  -->
</svg>"""
            
            # Save artifact
            safe_name = diagram_name.lower().replace(" ", "_").replace("/", "_")
            saved_path = self.artifact_manager.save_artifact(
                stage=ArtifactFolders.DIAGRAMS,
                base_name=f"{safe_name}_rendered",
                content=mock_svg_content,
                ext="svg"
            )
            
            rendered_svg_references[diagram_name] = saved_path
            artifacts_paths.append(saved_path)
            
            svg_metadata.append({
                "diagram": diagram_name,
                "svg_path": saved_path,
                "ready_for_react_ui": True
            })
            
        logger.info(f"Renderer Complete. Generated SVG metadata for {len(svg_metadata)} diagrams.")
        
        new_message = AIMessage(
            content=f"Rendered {len(rendered_svg_references)} diagrams into SVGs.",
            name="renderer"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "renderer_completed": True,
            "last_updated": generate_timestamp()
        }
        
        return {
            "svg_metadata": svg_metadata,
            "rendered_svg_references": rendered_svg_references,
            "artifacts": {
                ArtifactFolders.DIAGRAMS: artifacts_paths
            },
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "renderer"
        }

AgentRegistry().register(RendererAgent())
