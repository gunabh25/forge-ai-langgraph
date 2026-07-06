"""Unit tests for the VersionManager utility."""

import pytest
from core.versioning import VersionManager

def test_parse_filename_with_version():
    """Verify version details are correctly parsed from versioned filenames."""
    base, version, ext = VersionManager.parse_filename("requirements_v2.md")
    assert base == "requirements"
    assert version == 2
    assert ext == "md"

def test_parse_filename_without_version():
    """Verify default version (0) is returned for non-versioned filenames."""
    base, version, ext = VersionManager.parse_filename("architecture.md")
    assert base == "architecture"
    assert version == 0
    assert ext == "md"

def test_parse_filename_invalid_pattern():
    """Verify generic fallback matching when patterns do not match standard template."""
    base, version, ext = VersionManager.parse_filename("some_weird_file.txt")
    assert base == "some_weird_file"
    assert version == 0
    assert ext == "txt"

def test_generate_filename():
    """Verify versioned filename string format generation."""
    filename = VersionManager.generate_filename("backend_blueprint", 5, "json")
    assert filename == "backend_blueprint_v5.json"

def test_get_latest_version(tmp_path):
    """Verify correct scan of directory files to locate the highest version number."""
    dir_path = str(tmp_path)
    
    # Empty directory
    assert VersionManager.get_latest_version(dir_path, "requirements", "md") == 0
    
    # Add non-target and target files
    (tmp_path / "requirements_v1.md").write_text("v1 content")
    (tmp_path / "requirements_v3.md").write_text("v3 content")
    (tmp_path / "architecture_v4.md").write_text("arch content")
    (tmp_path / "requirements.txt").write_text("other text")
    
    # Scan matches
    assert VersionManager.get_latest_version(dir_path, "requirements", "md") == 3
    assert VersionManager.get_latest_version(dir_path, "architecture", "md") == 4
    assert VersionManager.get_latest_version(dir_path, "requirements", "txt") == 0

def test_get_next_filename(tmp_path):
    """Verify calculation of next sequential filename version."""
    dir_path = str(tmp_path)
    (tmp_path / "requirements_v1.md").write_text("v1 content")
    (tmp_path / "requirements_v2.md").write_text("v2 content")
    
    next_file = VersionManager.get_next_filename(dir_path, "requirements", "md")
    assert next_file == "requirements_v3.md"
