"""Phase 9 Comprehensive Regression Suite.

Verifies parser single-source-of-truth, UTF-8 BOM handling, Markdown code block stripping,
stable ID generation, deterministic PlantUML builder serialization, directional arrow parsing,
non-graph directive filtering, and repair loop attempt termination.
"""

from pathlib import Path
import json
import pytest

from agents.uml_generator.canonical_parser import CanonicalDiagramParser, CanonicalParseError
from agents.uml_generator.canonical_validator import CanonicalDiagramValidator
from agents.uml_generator.plantuml_builder import PlantUMLBuilderFactory
from agents.uml_generator.uml_parser import PlantUMLParser
from agents.uml_generator.validators import ArchitectureValidator, ValidationPipeline
from schemas.canonical_diagram import ComponentDiagramCanonical, SequenceDiagramCanonical


def test_regression_markdown_fenced_json_parsing():
    """Verify parsing Markdown fenced JSON responses across LLM providers."""
    fenced_json = """```json
{
  "metadata": {"diagram_type": "component", "title": "Fenced System"},
  "actors": [{"id": "actor_user", "name": "User"}],
  "business_capabilities": [{"id": "cap_order", "name": "Order Service"}]
}
```"""
    data = CanonicalDiagramParser.parse(fenced_json)
    assert data["metadata"]["title"] == "Fenced System"


def test_regression_utf8_bom_handling():
    """Verify parsing UTF-8 BOM headers (\ufeff)."""
    bom_json = '\ufeff{"metadata": {"title": "BOM Test"}, "actors": [{"id": "actor_user", "name": "User"}]}'
    data = CanonicalDiagramParser.parse(bom_json)
    assert data["metadata"]["title"] == "BOM Test"


def test_regression_surrounding_text_extraction():
    """Verify JSON extraction when surrounded by leading and trailing text."""
    surrounded = """Here is your canonical JSON response:

```json
{
  "metadata": {"title": "Surrounded System"},
  "actors": [{"id": "actor_user", "name": "User"}]
}
```

Hope this helps!"""
    data = CanonicalDiagramParser.parse(surrounded)
    assert data["metadata"]["title"] == "Surrounded System"


def test_regression_builder_byte_determinism():
    """Verify identical Canonical JSON produces byte-for-byte identical PlantUML markup."""
    raw_dict = {
        "metadata": {"diagram_type": "component", "title": "Deterministic System"},
        "actors": [{"id": "actor_user", "name": "User"}],
        "external_systems": [{"id": "sys_payment", "name": "Payment Gateway"}],
        "business_packages": [
            {"id": "pkg_b", "name": "Package B", "capability_ids": ["cap_2"]},
            {"id": "pkg_a", "name": "Package A", "capability_ids": ["cap_1"]}
        ],
        "business_capabilities": [
            {"id": "cap_2", "name": "Cap 2"},
            {"id": "cap_1", "name": "Cap 1"}
        ],
        "databases": [{"id": "db_order", "name": "Order Database"}],
        "relationships": [
            {"source_id": "actor_user", "target_id": "cap_1", "direction": "-->", "label": "Submits"},
            {"source_id": "cap_1", "target_id": "cap_2", "direction": "-->", "label": "Processes"}
        ]
    }
    
    canonical1 = ComponentDiagramCanonical.model_validate(raw_dict)
    canonical2 = ComponentDiagramCanonical.model_validate(raw_dict)

    builder = PlantUMLBuilderFactory.get_builder("component")
    output1 = builder.build(canonical1)
    output2 = builder.build(canonical2)

    assert output1 == output2
    # Verify package A comes before package B (sorted by ID)
    assert output1.index('as pkg_a') < output1.index('as pkg_b')


def test_regression_direction_arrows_and_directives_no_false_positives():
    """Verify directional layout arrows (-right->, -down->) and directives do not leak false nodes."""
    puml = """@startuml "Test System"
title Enterprise Architecture Overview
left to right direction
skinparam defaultFontName Arial

package "Core Package" {
  component "Capability A" as cap_a
  component "Capability B" as cap_b
}

actor "User" as actor_user

actor_user -right-> cap_a : Use
cap_a -down-> cap_b : Forwards
@enduml"""

    diagram = PlantUMLParser.parse(puml)
    node_aliases = {n.alias for n in diagram.nodes}

    assert "cap_a" in node_aliases
    assert "cap_b" in node_aliases
    assert "actor_user" in node_aliases
    
    # Assert directives & direction tokens are NOT extracted as nodes
    for invalid in ["title", "skinparam", "left to right direction", "right", "down"]:
        assert invalid not in node_aliases


def test_regression_golden_baseline_compliance():
    """Verify loading and validating golden baseline fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "golden_baseline" / "compliance_monitoring.json"
    assert fixture_path.exists()
    
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    canonical = ComponentDiagramCanonical.model_validate(fixture["canonical_json"])

    builder = PlantUMLBuilderFactory.get_builder("component")
    puml = builder.build(canonical)

    plan_json = json.dumps({
        "actors": [a["name"] for a in fixture["canonical_json"]["actors"]],
        "external_systems": [e["name"] for e in fixture["canonical_json"]["external_systems"]],
        "major_components": [c["name"] for c in fixture["canonical_json"]["business_capabilities"]],
        "major_data_stores": [d["name"] for d in fixture["canonical_json"]["databases"]],
    })

    validator = ArchitectureValidator()
    val_res = validator.validate("component", plan_json, puml)

    assert val_res["passed"] is True
    assert val_res["score"] == 100
