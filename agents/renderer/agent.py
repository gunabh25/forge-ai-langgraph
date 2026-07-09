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
        return "Invokes a real PlantUML rendering engine to generate SVGs and PNGs with deep diagnostics."
        
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
        self.artifact_manager = ArtifactManager()

    def _invoke_plantuml(self, puml_path: str) -> List[Dict[str, Any]]:
        """Attempt to render a .puml file to SVG and PNG, capturing stdout/stderr."""
        results = []
        
        for fmt in ["svg", "png"]:
            cmd_plantuml = ["plantuml", f"-t{fmt}", puml_path]
            cmd_java = ["java", "-jar", "plantuml.jar", f"-t{fmt}", puml_path]
            
            res = {
                "format": fmt,
                "command": "",
                "returncode": -1,
                "stdout": "",
                "stderr": "",
                "status": "failed",
                "reason": "Unknown error"
            }
            
            # Try local plantuml command
            try:
                res["command"] = " ".join(cmd_plantuml)
                logger.info(f"Rendering diagram:\n{os.path.basename(puml_path)}\nCommand:\n{res['command']}")
                proc = subprocess.run(cmd_plantuml, check=False, capture_output=True, text=True)
                res["returncode"] = proc.returncode
                res["stdout"] = proc.stdout
                res["stderr"] = proc.stderr
                if proc.returncode == 0:
                    res["status"] = "success"
                    res["reason"] = ""
                else:
                    err_lower = proc.stderr.lower()
                    if "dot" in err_lower and ("not found" in err_lower or "executable" in err_lower):
                        res["reason"] = "Graphviz missing"
                    elif proc.stderr.strip() == "" and proc.stdout.strip() != "":
                        # Sometimes plantuml writes errors to stdout
                        res["reason"] = "PlantUML syntax error or execution failure"
                        res["stderr"] = proc.stdout
                    else:
                        res["reason"] = "PlantUML syntax error"
                results.append(res)
                continue
            except FileNotFoundError:
                pass
            except Exception as e:
                res["reason"] = f"Unexpected exception: {str(e)}"
                results.append(res)
                continue

            # Try java -jar plantuml.jar
            try:
                res["command"] = " ".join(cmd_java)
                logger.info(f"Rendering diagram:\n{os.path.basename(puml_path)}\nCommand:\n{res['command']}")
                proc = subprocess.run(cmd_java, check=False, capture_output=True, text=True)
                res["returncode"] = proc.returncode
                res["stdout"] = proc.stdout
                res["stderr"] = proc.stderr
                if proc.returncode == 0:
                    res["status"] = "success"
                    res["reason"] = ""
                else:
                    err_lower = proc.stderr.lower()
                    if "dot" in err_lower and ("not found" in err_lower or "executable" in err_lower):
                        res["reason"] = "Graphviz missing"
                    else:
                        res["reason"] = "PlantUML syntax error"
                results.append(res)
                continue
            except FileNotFoundError:
                res["reason"] = "Renderer not installed"
                results.append(res)
            except Exception as e:
                res["reason"] = f"Unexpected exception: {str(e)}"
                results.append(res)
                
        return results

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
        start_time = time.time()
        
        successful_files = []
        failed_files = []
        
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
                successful_files.append(diagram_name)
                continue

            # 1. Write the .puml file
            puml_path = self.artifact_manager.save_artifact(
                stage=ArtifactFolders.DIAGRAMS,
                base_name=f"{safe_name}",
                content=puml_content,
                ext="puml"
            )
            artifacts_paths.append(puml_path)
            
            if not os.path.exists(puml_path):
                render_success = False
                failed_files.append({
                    "diagram": diagram_name,
                    "status": "failed",
                    "reason": "File not found (Failed to save .puml to disk)",
                    "stderr": "",
                    "return_code": -1,
                    "command": ""
                })
                continue

            # 2. Invoke rendering engine
            invoke_results = self._invoke_plantuml(puml_path)
            
            # The PlantUML engine places the outputs in the same directory as the .puml file
            expected_svg = puml_path.replace(".puml", ".svg")
            expected_png = puml_path.replace(".puml", ".png")
            
            diagram_success = True
            diagram_reason = ""
            diagram_stderr = ""
            diagram_stdout = ""
            diagram_returncode = 0
            diagram_command = ""
            
            for res in invoke_results:
                if res["status"] != "success":
                    diagram_success = False
                    diagram_reason = res["reason"]
                    diagram_stderr = res["stderr"]
                    diagram_stdout = res["stdout"]
                    diagram_returncode = res["returncode"]
                    diagram_command = res["command"]
                    break
            
            # 3. Validation
            if diagram_success:
                if not os.path.exists(expected_svg):
                    diagram_success = False
                    diagram_reason = "Output file missing (.svg)"
                elif os.path.getsize(expected_svg) == 0:
                    diagram_success = False
                    diagram_reason = "Output file empty (.svg)"
                elif not os.path.exists(expected_png):
                    diagram_success = False
                    diagram_reason = "Output file missing (.png)"
                elif os.path.getsize(expected_png) == 0:
                    diagram_success = False
                    diagram_reason = "Output file empty (.png)"
            
            if diagram_success:
                rendered_svg_references[diagram_name] = expected_svg
                artifacts_paths.extend([expected_svg, expected_png])
                
                svg_metadata.append({
                    "diagram": diagram_name,
                    "svg_path": expected_svg,
                    "png_path": expected_png,
                    "puml_path": puml_path,
                    "ready_for_react_ui": True
                })
                successful_files.append(diagram_name)
            else:
                render_success = False
                logger.error(f"Failed to render {diagram_name}. Reason: {diagram_reason}")
                
                # Fetch command info from the first attempt if it failed validation but passed invocation
                if not diagram_command and invoke_results:
                    diagram_command = invoke_results[0]["command"]
                    diagram_returncode = invoke_results[0]["returncode"]
                    
                failed_files.append({
                    "diagram": diagram_name,
                    "status": "failed",
                    "reason": diagram_reason,
                    "stderr": diagram_stderr,
                    "return_code": diagram_returncode,
                    "command": diagram_command
                })

        render_time_ms = int((time.time() - start_time) * 1000)

        # Build Summary
        summary_lines = [
            "Renderer Summary",
            "Engine: PlantUML",
            f"Successful: {len(successful_files)}",
            f"Failed: {len(failed_files)}"
        ]
        
        if failed_files:
            summary_lines.append("\nFailure Reasons")
            for f in failed_files:
                summary_lines.append(f"\n{f['diagram']}")
                summary_lines.append(f"{f['reason']}")

        summary_text = "\n".join(summary_lines)
        logger.info(f"\n{summary_text}")
        
        new_message = AIMessage(
            content=f"Renderer execution complete.\n\n{summary_text}",
            name="renderer"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        
        execution_report = {
            "render_engine": "PlantUML",
            "render_time_ms": render_time_ms,
            "render_success": render_success,
            "rendered_files": successful_files,
            "failed_files": failed_files
        }
        
        updated_metadata = {
            **current_metadata,
            "renderer_completed": True,
            "render_success": render_success,
            "render_engine": "PlantUML",
            "render_time_ms": render_time_ms,
            "renderer_execution_report": execution_report,
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
