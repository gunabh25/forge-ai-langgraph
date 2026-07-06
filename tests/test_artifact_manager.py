"""Unit tests for the ArtifactManager utility."""

import os
import pytest
from core.artifact_manager import ArtifactManager

def test_artifact_manager_directories(tmp_path):
    """Verify initialization and directory resolution in ArtifactManager."""
    manager = ArtifactManager(root_dir=str(tmp_path))
    stage_dir = manager.get_stage_directory("requirements")
    assert stage_dir == os.path.abspath(os.path.join(tmp_path, "requirements"))

def test_ensure_directories(tmp_path):
    """Verify that required stage folders are initialized properly."""
    manager = ArtifactManager(root_dir=str(tmp_path))
    stages = ["requirements", "architecture"]
    manager.ensure_directories(stages)
    
    assert os.path.isdir(os.path.join(tmp_path, "requirements"))
    assert os.path.isdir(os.path.join(tmp_path, "architecture"))

def test_save_and_load_artifact(tmp_path):
    """Verify saving a new artifact and loading the latest version."""
    manager = ArtifactManager(root_dir=str(tmp_path))
    
    # Save v1
    path_v1 = manager.save_artifact("requirements", "requirements", "Requirement Details v1", "md")
    assert "requirements_v1.md" in path_v1
    assert os.path.exists(path_v1)
    
    # Save v2
    path_v2 = manager.save_artifact("requirements", "requirements", "Requirement Details v2", "md")
    assert "requirements_v2.md" in path_v2
    
    # Load latest version (should be v2)
    content, loaded_path = manager.load_latest_artifact("requirements", "requirements", "md")
    assert content == "Requirement Details v2"
    assert loaded_path == path_v2

def test_list_artifact_versions(tmp_path):
    """Verify listing all version paths in ascending order."""
    manager = ArtifactManager(root_dir=str(tmp_path))
    
    manager.save_artifact("architecture", "arch", "arch v1", "md")
    manager.save_artifact("architecture", "arch", "arch v2", "md")
    
    versions = manager.list_artifact_versions("architecture", "arch", "md")
    assert len(versions) == 2
    assert versions[0][0] == 1
    assert "arch_v1.md" in versions[0][1]
    assert versions[1][0] == 2
    assert "arch_v2.md" in versions[1][1]
