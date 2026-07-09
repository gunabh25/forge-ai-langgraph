"""Renderer Agent implementation."""

import json
import os
import subprocess
import time
from typing import Dict, Any, List, Optional
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
    """Renderer Agent responsible for production-grade rendering of PlantUML to SVG/PNG."""
    
    @property
    def name(self) -> str:
        return "Renderer Agent"
        
    @property
    def description(self) -> str:
        return "Invokes a real PlantUML rendering engine to generate SVGs and PNGs."
        
    @property
    def capabilities(self) -> List[str]:
        return ["plantuml_rendering", "svg_generation", "png_generation"]

    @property
    def requires(self) -> List[str]:
        return ["plantuml_validation_report"]

    @property
    def produces(self) -> List[str]:
        return ["rendered_svg_references"]

    def __init__(self):
        # We no longer instantiate or need self._llm since rendering is deterministic
        self.artifact_manager = ArtifactManager()

    def _invoke_plantuml(self, puml_path: str) -> bool:
        """Attempt to render a .puml file using 'plantuml' or 'java -jar plantuml.jar'."""
        # Try local plantuml command
        try:
            # -tsvg generates SVG, -tpng generates PNG
            subprocess.run(["plantuml", "-tsvg", puml_path], check=True, capture_output=True)
            subprocess.run(["plantuml", "-tpng", puml_path], check=True, capture_output=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        # Try plantuml.jar
        try:
            subprocess.run(["java", "-jar", "plantuml.jar", "-tsvg", puml_path], check=True, capture_output=True)
            subprocess.run(["java", "-jar", "plantuml.jar", "-tpng", puml_path], check=True, capture_output=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        return False

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
        
        render_success = True
        renderer_error = None
        start_time = time.time()
        
        for diagram_name, puml_content in plantuml_diagrams.items():
            safe_name = diagram_name.lower().replace(" ", "_").replace("/", "_")
            
            if diagram_name.lower() not in selected_diagrams and diagram_name in rendered_svg_references:
                logger.info(f"Reusing existing SVG for {diagram_name}...")
                svg_path = rendered_svg_references[diagram_name]
                png_path = svg_path.replace(".svg", ".png")
                puml_path = svg_path.replace(".svg", ".puml")
                
                svg_metadata.append({
                    "diagram": diagram_name,
                    "svg_path": svg_path,
                    "png_path": png_path,
                    "puml_path": puml_path,
                    "ready_for_react_ui": True
                })
                artifacts_paths.extend([svg_path, png_path, puml_path])
                continue

            # 1. Write the .puml file
            puml_path = self.artifact_manager.save_artifact(
                stage=ArtifactFolders.DIAGRAMS,
                base_name=f"{safe_name}",
                content=puml_content,
                ext="puml"
            )
            artifacts_paths.append(puml_path)
            
            # Ensure the artifact manager wrote to disk
            if not os.path.exists(puml_path):
                render_success = False
                renderer_error = f"Failed to save {puml_path} to disk."
                continue

            # 2. Invoke rendering engine
            success = self._invoke_plantuml(puml_path)
            
            # The PlantUML engine places the outputs in the same directory as the .puml file
            expected_svg = puml_path.replace(".puml", ".svg")
            expected_png = puml_path.replace(".puml", ".png")
            
            # 3. Validation
            svg_generated = os.path.exists(expected_svg) and os.path.getsize(expected_svg) > 0
            png_generated = os.path.exists(expected_png) and os.path.getsize(expected_png) > 0
            
            if success and svg_generated and png_generated:
                rendered_svg_references[diagram_name] = expected_svg
                artifacts_paths.extend([expected_svg, expected_png])
                
                svg_metadata.append({
                    "diagram": diagram_name,
                    "svg_path": expected_svg,
                    "png_path": expected_png,
                    "puml_path": puml_path,
                    "ready_for_react_ui": True
                })
            else:
                render_success = False
                renderer_error = "PlantUML rendering engine unavailable or failed to produce valid artifacts."
                logger.error(f"Failed to render {diagram_name}. Engine unavailable.")

        render_time_ms = int((time.time() - start_time) * 1000)

        logger.info(f"Renderer Complete. Generated SVG metadata for {len(svg_metadata)} diagrams.")
        
        new_message = AIMessage(
            content=f"Rendered {len(rendered_svg_references)} diagrams into SVGs.",
            name="renderer"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "renderer_completed": True,
            "render_success": render_success,
            "render_engine": "PlantUML",
            "render_time_ms": render_time_ms,
            "renderer_error": renderer_error,
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
