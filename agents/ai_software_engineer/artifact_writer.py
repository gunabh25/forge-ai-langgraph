import os
import json
from typing import List, Dict, Any

from core.artifact_manager import ArtifactManager
from core.constants import ArtifactFolders
from core.utils import ensure_directory, safe_write_file

class ArtifactWriter:
    """Handles writing validated files to disk incrementally."""

    def __init__(self, artifact_manager: ArtifactManager):
        self.artifact_manager = artifact_manager
        
        # Determine base generated directory
        self.generated_base = os.path.join(
            self.artifact_manager.get_stage_directory(ArtifactFolders.IMPLEMENTATION),
            "generated",
        )
        ensure_directory(self.generated_base)
        
    def save_project_manifest(self, manifest: Dict[str, Any]) -> str:
        """Save the JSON project manifest."""
        return self.artifact_manager.save_artifact(
            stage=ArtifactFolders.IMPLEMENTATION,
            base_name="project_manifest",
            content=json.dumps(manifest, indent=2),
            ext="json"
        )
        
    def save_file(self, rel_path: str, content: str) -> str:
        """Save a single generated source code file."""
        abs_path = os.path.join(self.generated_base, rel_path)
        safe_write_file(abs_path, content)
        return abs_path

    def update_implementation_manifest(
        self, 
        workspace_generated: List[str], 
        workspace_failed: List[str], 
        workspace_skipped: List[str]
    ) -> str:
        """Create/update the markdown manifest of files."""
        lines = [
            "# Implementation Manifest",
            "",
            f"**Total files generated**: {len(workspace_generated)}",
            f"**Total files skipped (cached)**: {len(workspace_skipped)}",
            f"**Total files failed**: {len(workspace_failed)}",
            "",
        ]
        
        if workspace_generated:
            lines.extend(["## Generated Files", ""])
            for rel_path in sorted(workspace_generated):
                lines.append(f"- `[x]` `{rel_path}`")
            lines.append("")
            
        if workspace_skipped:
            lines.extend(["## Skipped Files (Cached)", ""])
            for rel_path in sorted(workspace_skipped):
                lines.append(f"- `[-]` `{rel_path}`")
            lines.append("")
            
        if workspace_failed:
            lines.extend(["## Failed Files", ""])
            for rel_path in sorted(workspace_failed):
                lines.append(f"- `[ ]` `{rel_path}`")
            lines.append("")
            
        lines.extend([
            "## Artifact Locations",
            "",
            "Files are stored under `artifacts/implementation/generated/`.",
        ])
        
        manifest_content = "\n".join(lines)
        
        # We can just save a new version of the implementation manifest.
        return self.artifact_manager.save_artifact(
            stage=ArtifactFolders.IMPLEMENTATION,
            base_name="implementation_manifest",
            content=manifest_content,
            ext="md",
        )
