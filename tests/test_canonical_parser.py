"""Unit tests for CanonicalDiagramParser and Single Source of Truth compliance."""

import re
from pathlib import Path
import pytest
from agents.uml_generator.canonical_parser import CanonicalDiagramParser, CanonicalParseError


def test_parse_raw_json():
    """Test parsing raw JSON string."""
    raw = '{"metadata": {"title": "Test Diagram"}}'
    result = CanonicalDiagramParser.parse(raw)
    assert result == {"metadata": {"title": "Test Diagram"}}


def test_parse_markdown_json_fenced():
    """Test parsing Markdown ```json fenced JSON string."""
    raw = '```json\n{"metadata": {"title": "Fenced JSON"}}\n```'
    result = CanonicalDiagramParser.parse(raw)
    assert result == {"metadata": {"title": "Fenced JSON"}}


def test_parse_markdown_generic_fenced():
    """Test parsing generic ``` fenced JSON string."""
    raw = '```\n{"metadata": {"title": "Generic Fenced"}}\n```'
    result = CanonicalDiagramParser.parse(raw)
    assert result == {"metadata": {"title": "Generic Fenced"}}


def test_parse_leading_explanatory_text():
    """Test parsing JSON with leading explanatory text before JSON block."""
    raw = 'Here is the requested Canonical Diagram JSON:\n\n{"metadata": {"title": "Leading Text"}}'
    result = CanonicalDiagramParser.parse(raw)
    assert result == {"metadata": {"title": "Leading Text"}}


def test_parse_trailing_explanatory_text():
    """Test parsing JSON with trailing text after JSON block."""
    raw = '{"metadata": {"title": "Trailing Text"}}\n\nHope this helps!'
    result = CanonicalDiagramParser.parse(raw)
    assert result == {"metadata": {"title": "Trailing Text"}}


def test_parse_utf8_bom():
    """Test parsing JSON string with UTF-8 BOM header."""
    raw = '\ufeff{"metadata": {"title": "BOM Test"}}'
    result = CanonicalDiagramParser.parse(raw)
    assert result == {"metadata": {"title": "BOM Test"}}


def test_parse_extra_blank_lines():
    """Test parsing JSON string surrounded by whitespace and blank lines."""
    raw = '\n\n  \n{"metadata": {"title": "Blank Lines"}}\n  \n'
    result = CanonicalDiagramParser.parse(raw)
    assert result == {"metadata": {"title": "Blank Lines"}}


def test_parse_dict_passthrough():
    """Test pass-through when input is already a dictionary."""
    data = {"metadata": {"title": "Dict Pass-through"}}
    result = CanonicalDiagramParser.parse(data)
    assert result == data


def test_parse_invalid_json_raises_canonical_parse_error():
    """Test invalid JSON syntax raises descriptive CanonicalParseError."""
    raw = '{"metadata": {bad syntax}}'
    with pytest.raises(CanonicalParseError) as exc_info:
        CanonicalDiagramParser.parse(raw)
    err = exc_info.value
    assert err.stage == "json_decoding"
    assert "Invalid JSON syntax" in str(err)
    assert err.response_len == len(raw)


def test_parse_missing_json_raises_canonical_parse_error():
    """Test response lacking braces raises descriptive CanonicalParseError."""
    raw = 'No JSON content here.'
    with pytest.raises(CanonicalParseError) as exc_info:
        CanonicalDiagramParser.parse(raw)
    err = exc_info.value
    assert err.stage == "json_object_extraction"
    assert "No JSON object bounded by '{' and '}' found" in str(err)


def test_parse_nested_json():
    """Test parsing complex nested Canonical Diagram JSON."""
    raw = """
    Here is your canonical diagram:
    ```json
    {
      "metadata": {"diagram_type": "component", "title": "Nested System"},
      "actors": [{"id": "actor_user", "name": "User"}],
      "business_packages": [
        {"id": "pkg_core", "name": "Core Package", "capability_ids": ["cap_order"]}
      ],
      "business_capabilities": [{"id": "cap_order", "name": "Order Service"}],
      "relationships": [
        {"source_id": "actor_user", "target_id": "cap_order", "direction": "-->", "label": "Submits"}
      ]
    }
    ```
    Best regards!
    """
    result = CanonicalDiagramParser.parse(raw)
    assert result["metadata"]["title"] == "Nested System"
    assert len(result["relationships"]) == 1


def test_architecture_single_source_of_truth_compliance():
    """Static compliance test ensuring raw LLM response parsing in UML pipeline routes through CanonicalDiagramParser."""
    agents_dir = Path(__file__).parent.parent / "agents"
    
    # Target canonical diagram generation and validation files
    pipeline_files = [
        agents_dir / "uml_generator" / "canonical_validator.py",
        agents_dir / "uml_repair" / "targeted_patcher.py",
    ]

    for file_path in pipeline_files:
        assert file_path.exists(), f"File {file_path} missing for compliance check."
        content = file_path.read_text(encoding="utf-8")
        
        # Check that json.loads is not called directly on raw response strings in these files
        matches = [line for line in content.splitlines() if "json.loads(" in line and "CanonicalDiagramParser" not in line]
        assert not matches, f"Direct un-guarded json.loads found in {file_path.name}: {matches}"
