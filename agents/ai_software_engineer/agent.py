import os
import json
from typing import Dict, Any, Optional, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage

from app.state import ForgeState
from config.logging import get_logger
from core.artifact_manager import ArtifactManager
from core.constants import ArtifactFolders, WorkflowStages
from core.llm import get_llm
from core.utils import generate_timestamp

from agents.ai_software_engineer.manifest_generator import ManifestGenerator
from agents.ai_software_engineer.file_planner import FilePlanner
from agents.ai_software_engineer.file_generator import FileGenerator
from agents.ai_software_engineer.validator import Validator
from agents.ai_software_engineer.artifact_writer import ArtifactWriter
from agents.ai_software_engineer.progress_tracker import ProgressTracker

logger = get_logger("agents.ai_software_engineer")

class AISoftwareEngineerAgent:
    """AI Software Engineer agent that generates a complete project workspace internally using a multi-stage pipeline."""

    def __init__(self, llm: Optional[BaseChatModel] = None) -> None:
        self._llm = llm
        self.artifact_manager = ArtifactManager()
        self.artifact_writer = ArtifactWriter(self.artifact_manager)
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the AI Software Engineer agent step."""
        logger.info("Implementation started")

        requirements = (state.get("requirements") or "").strip()
        architecture = (state.get("architecture") or "").strip()
        backend_blueprint = (state.get("backend_blueprint") or "").strip()

        if not requirements or not architecture or not backend_blueprint:
            raise ValueError("AI Software Engineer: Missing required state fields (requirements, architecture, backend_blueprint)")

        # 1. Manifest Generator
        manifest_gen = ManifestGenerator(self.llm)
        manifest = manifest_gen.generate(requirements, architecture, backend_blueprint)
        self.artifact_writer.save_project_manifest(manifest)
        
        # 2. File Planner
        planner = FilePlanner(manifest)
        file_queue = planner.get_file_queue()
        
        # 3. Progress Tracker
        tracker = ProgressTracker(total_files=len(file_queue))
        tracker.set_pending(file_queue)
        
        # 4. File Generator
        file_gen = FileGenerator(self.llm)
        
        generated_files = {}
        workspace_generated = []
        workspace_failed = []
        workspace_skipped = []
        
        for file_path in file_queue:
            abs_path = os.path.join(self.artifact_writer.generated_base, file_path)
            
            # Resume Capability
            if os.path.exists(abs_path):
                with open(abs_path, "r", encoding="utf-8") as f:
                    generated_files[file_path] = f.read()
                workspace_skipped.append(file_path)
                tracker.mark_skipped(file_path)
                continue
                
            success = False
            feedback = None
            retries = 3
            
            while retries > 0 and not success:
                try:
                    content = file_gen.generate(
                        file_path=file_path,
                        requirements=requirements,
                        architecture=architecture,
                        backend_blueprint=backend_blueprint,
                        manifest=manifest,
                        feedback=feedback,
                        previously_generated=generated_files
                    )
                    
                    # 5. Validator
                    is_valid, error_msg = Validator.validate(file_path, content)
                    
                    if is_valid:
                        # 6. Artifact Writer
                        self.artifact_writer.save_file(file_path, content)
                        generated_files[file_path] = content
                        workspace_generated.append(file_path)
                        tracker.mark_completed(file_path)
                        success = True
                    else:
                        feedback = error_msg
                        retries -= 1
                except Exception as e:
                    feedback = str(e)
                    retries -= 1
                    
            if not success:
                workspace_failed.append(file_path)
                tracker.mark_failed(file_path)

        # Update implementation manifest
        manifest_path = self.artifact_writer.update_implementation_manifest(
            workspace_generated, workspace_failed, workspace_skipped
        )

        file_count = len(workspace_generated) + len(workspace_skipped)
        summary_lines = [
            f"Implementation complete. Total files: {file_count}",
            f"Generated newly: {len(workspace_generated)}",
            f"Skipped (cached): {len(workspace_skipped)}",
            f"Failed: {len(workspace_failed)}"
        ]
        implementation_summary = "\n".join(summary_lines)
        
        new_message = AIMessage(content=implementation_summary, name="ai_software_engineer")

        current_metadata = dict(state.get("metadata") or {})
        updated_metadata = {
            **current_metadata,
            "ai_software_engineering_completed": True,
            "generated_file_count": file_count,
            "failed_file_count": len(workspace_failed),
            "last_updated": generate_timestamp(),
        }

        saved_file_paths = []
        for file_path in generated_files.keys():
            saved_file_paths.append(os.path.join(self.artifact_writer.generated_base, file_path))

        state_updates = {
            "implementation": implementation_summary,
            "generated_files": generated_files,
            "artifacts": {
                ArtifactFolders.IMPLEMENTATION: [manifest_path] + saved_file_paths
            },
            "current_stage": WorkflowStages.AI_SOFTWARE_ENGINEERING,
            "messages": [new_message],
            "metadata": updated_metadata,
        }

        logger.info("Implementation completed")
        return state_updates
