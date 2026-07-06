"""Version management utilities for artifact storage."""

import os
import re
from typing import Tuple

# Pattern matching filenames of the form: {base_name}_v{version}.{extension}
VERSION_PATTERN = re.compile(r"^(.*?)(?:_v(\d+))?\.(.+)$")

class VersionManager:
    """Class to parse artifact names and manage sequential file versioning."""
    
    @staticmethod
    def parse_filename(filename: str) -> Tuple[str, int, str]:
        """Parse a filename into base name, version integer, and extension.
        
        Examples:
            "requirements_v2.md" -> ("requirements", 2, "md")
            "architecture.md"    -> ("architecture", 0, "md")
            
        Args:
            filename: String filename.
            
        Returns:
            Tuple of (base_name, version, extension).
        """
        match = VERSION_PATTERN.match(filename)
        if not match:
            name, ext = os.path.splitext(filename)
            return name, 0, ext.lstrip(".")
            
        base_name, version_str, ext = match.groups()
        version = int(version_str) if version_str else 0
        return base_name, version, ext

    @staticmethod
    def get_latest_version(directory: str, base_name: str, ext: str) -> int:
        """Scan the directory to find the highest version of the specified artifact.
        
        Args:
            directory: Directory path to scan.
            base_name: Target base filename to match (e.g. "requirements").
            ext: File extension to match (e.g. "md").
            
        Returns:
            The highest version number found, or 0 if none exist.
        """
        if not os.path.exists(directory):
            return 0
            
        max_version = 0
        for entry in os.listdir(directory):
            entry_path = os.path.join(directory, entry)
            if not os.path.isfile(entry_path):
                continue
                
            entry_base, version, entry_ext = VersionManager.parse_filename(entry)
            if entry_base == base_name and entry_ext == ext:
                max_version = max(max_version, version)
                
        return max_version

    @staticmethod
    def generate_filename(base_name: str, version: int, ext: str) -> str:
        """Generate a versioned filename.
        
        Args:
            base_name: Base file descriptor.
            version: Version number.
            ext: Extension.
            
        Returns:
            String filename formatted with version extension.
        """
        return f"{base_name}_v{version}.{ext}"

    @staticmethod
    def get_next_filename(directory: str, base_name: str, ext: str) -> str:
        """Determine the next version number and return its filename.
        
        Args:
            directory: Directory target folder.
            base_name: Base filename.
            ext: Target extension.
            
        Returns:
            Filename for the next sequential version.
        """
        latest = VersionManager.get_latest_version(directory, base_name, ext)
        next_ver = latest + 1
        return VersionManager.generate_filename(base_name, next_ver, ext)
