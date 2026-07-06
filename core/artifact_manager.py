"""Asset and artifact management system for ForgeAI."""

import os
from typing import Optional, List, Tuple
from app.settings import settings
from core.versioning import VersionManager
from core.utils import safe_write_file, ensure_directory

class ArtifactManager:
    """Manager class to load, version, list, and write artifacts to disk."""
    
    def __init__(self, root_dir: Optional[str] = None):
        """Initialize ArtifactManager.
        
        Args:
            root_dir: The base directory for artifacts. Defaults to settings.ARTIFACT_ROOT.
        """
        self.root_dir = root_dir or settings.ARTIFACT_ROOT

    def get_stage_directory(self, stage: str) -> str:
        """Get the absolute path for a specific workflow stage folder.
        
        Args:
            stage: The name of the stage/folder.
            
        Returns:
            Absolute folder path.
        """
        return os.path.abspath(os.path.join(self.root_dir, stage))

    def ensure_directories(self, stages: List[str]) -> None:
        """Create directories for the provided stage keys.
        
        Args:
            stages: List of stage directory subfolder names.
        """
        for stage in stages:
            ensure_directory(self.get_stage_directory(stage))

    def save_artifact(self, stage: str, base_name: str, content: str, ext: str = "md") -> str:
        """Save a new version of the artifact to its appropriate stage folder.
        
        Args:
            stage: Target folder/stage name.
            base_name: Artifact base name.
            content: Raw string content.
            ext: File extension (default "md").
            
        Returns:
            Absolute filepath to the saved file.
        """
        dir_path = self.get_stage_directory(stage)
        ensure_directory(dir_path)
        
        filename = VersionManager.get_next_filename(dir_path, base_name, ext)
        full_path = os.path.join(dir_path, filename)
        safe_write_file(full_path, content)
        return full_path

    def load_latest_artifact(self, stage: str, base_name: str, ext: str = "md") -> Tuple[Optional[str], Optional[str]]:
        """Load content and filepath of the latest version of an artifact.
        
        Args:
            stage: Folder/stage name.
            base_name: Artifact base name.
            ext: File extension.
            
        Returns:
            Tuple of (file_content, absolute_filepath) if found, otherwise (None, None).
        """
        dir_path = self.get_stage_directory(stage)
        latest_ver = VersionManager.get_latest_version(dir_path, base_name, ext)
        if latest_ver == 0:
            return None, None
            
        filename = VersionManager.generate_filename(base_name, latest_ver, ext)
        full_path = os.path.join(dir_path, filename)
        
        if not os.path.exists(full_path):
            return None, None
            
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read(), full_path

    def list_artifact_versions(self, stage: str, base_name: str, ext: str = "md") -> List[Tuple[int, str]]:
        """List all version numbers and filepaths for a given artifact.
        
        Args:
            stage: Target stage directory.
            base_name: Artifact base name.
            ext: Extension.
            
        Returns:
            List of (version_integer, absolute_filepath) sorted in ascending order of version.
        """
        dir_path = self.get_stage_directory(stage)
        if not os.path.exists(dir_path):
            return []
            
        versions = []
        for entry in os.listdir(dir_path):
            entry_base, version, entry_ext = VersionManager.parse_filename(entry)
            if entry_base == base_name and entry_ext == ext and version > 0:
                versions.append((version, os.path.abspath(os.path.join(dir_path, entry))))
                
        return sorted(versions, key=lambda x: x[0])
