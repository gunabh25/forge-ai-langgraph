"""Renderer Agent implementation."""

import json
from typing import Dict, Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage
from agents.base import BaseAgent
from core.llm import get_llm
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

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Renderer Agent."""
        logger.info("Renderer Agent starting execution.")
        
        plantuml_diagrams = state.get("plantuml_diagrams", {})
        if not plantuml_diagrams:
            logger.warning("No PlantUML diagrams found to render.")
            return {}

        rendered_svg_references = dict(state.get("rendered_svg_references", {}) or {})
        svg_metadata = []
        artifacts_paths = []
        
        selected_diagrams = {d.get("diagram", "").lower() for d in (state.get("selected_uml_diagrams") or [])}
        
        for diagram_name, puml_content in plantuml_diagrams.items():
            if diagram_name.lower() not in selected_diagrams and diagram_name in rendered_svg_references:
                logger.info(f"Reusing existing SVG for {diagram_name}...")
                svg_path = rendered_svg_references[diagram_name]
                png_path = svg_path.replace(".svg", ".png")
                mermaid_path = svg_path.replace(".svg", ".mmd")
                
                svg_metadata.append({
                    "diagram": diagram_name,
                    "svg_path": svg_path,
                    "png_path": png_path,
                    "mermaid_path": mermaid_path,
                    "ready_for_react_ui": True
                })
                artifacts_paths.extend([svg_path, png_path, mermaid_path])
                continue

            # Create a mock SVG that simply wraps the PlantUML syntax 
            # (In production, this would call a PlantUML jar or API)
            mock_svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg">
  <desc>Mock SVG for {diagram_name}</desc>
  <!-- PlantUML Source:
{puml_content}
  -->
</svg>"""
            
            # Generate Mock PNG
            mock_png_content = f"Mock PNG binary wrapper for {diagram_name}\\n(In production, this would be binary PNG data)"
            
            # Generate Mermaid via LLM
            logger.info(f"Invoking LLM to convert {diagram_name} to Mermaid...")
            mermaid_prompt = f"Convert the following PlantUML to Mermaid syntax. Return ONLY the raw Mermaid code, no markdown wrappers.\\n\\n{puml_content}"
            from langchain_core.messages import HumanMessage
            mermaid_response = self.llm.invoke([HumanMessage(content=mermaid_prompt)])
            mermaid_content = str(mermaid_response.content).replace("```mermaid", "").replace("```", "").strip()
            
            # Save artifacts
            safe_name = diagram_name.lower().replace(" ", "_").replace("/", "_")
            
            svg_path = self.artifact_manager.save_artifact(
                stage=ArtifactFolders.DIAGRAMS,
                base_name=f"{safe_name}",
                content=mock_svg_content,
                ext="svg"
            )
            
            png_path = self.artifact_manager.save_artifact(
                stage=ArtifactFolders.DIAGRAMS,
                base_name=f"{safe_name}",
                content=mock_png_content,
                ext="png"
            )
            
            mermaid_path = self.artifact_manager.save_artifact(
                stage=ArtifactFolders.DIAGRAMS,
                base_name=f"{safe_name}",
                content=mermaid_content,
                ext="mmd"
            )
            
            rendered_svg_references[diagram_name] = svg_path
            artifacts_paths.extend([svg_path, png_path, mermaid_path])
            
            svg_metadata.append({
                "diagram": diagram_name,
                "svg_path": svg_path,
                "png_path": png_path,
                "mermaid_path": mermaid_path,
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
