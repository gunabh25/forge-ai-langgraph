"""Regression test suite for sequence self-loop prevention and repair."""

import json
import pytest
from schemas.canonical_diagram import SequenceDiagramCanonical
from agents.uml_generator.canonical_validator import CanonicalDiagramValidator, CanonicalValidationError
from agents.uml_generator.validators import ArchitectureValidator
from agents.uml_repair.targeted_patcher import TargetedPatcher, TargetedRepairPatch
from agents.uml_generator.plantuml_builder import PlantUMLBuilderFactory


def test_canonical_validator_detects_sequence_self_loop():
    """Verify CanonicalDiagramValidator detects sequence self-loops."""
    data = {
        "metadata": {"diagram_type": "sequence", "title": "Self Loop Test"},
        "actors": [{"id": "actor_user", "name": "User"}],
        "business_capabilities": [{"id": "cap_analysis", "name": "Analysis Engine"}],
        "participants": ["actor_user", "cap_analysis"],
        "relationships": [
            {"source_id": "actor_user", "target_id": "cap_analysis", "direction": "->", "label": "Start"},
            {"source_id": "cap_analysis", "target_id": "cap_analysis", "direction": "->", "label": "Perform Gap Analysis"}
        ]
    }
    
    diagram = SequenceDiagramCanonical.model_validate(data)
    with pytest.raises(CanonicalValidationError) as exc:
        CanonicalDiagramValidator.validate_references(diagram)
    
    assert "Self-loop interaction detected" in str(exc.value)


def test_architecture_validator_classifies_self_loop_interaction():
    """Verify ArchitectureValidator returns SELF_LOOP_INTERACTION diagnostic code."""
    puml = """@startuml
actor "User" as actor_user
participant "Analysis Engine" as cap_analysis

actor_user -> cap_analysis : Start
cap_analysis -> cap_analysis : Internal Computation
@enduml"""

    plan_json = json.dumps({
        "actors": ["User"],
        "major_components": ["Analysis Engine"],
        "external_systems": [],
        "major_data_stores": []
    })

    validator = ArchitectureValidator()
    res = validator.validate("sequence", plan_json, puml)

    assert res["passed"] is False
    assert any(d["code"] == "SELF_LOOP_INTERACTION" for d in res["diagnostics"])


def test_targeted_patcher_sanitizes_self_loops():
    """Verify TargetedPatcher strips self-loops during patch application."""
    data = {
        "metadata": {"diagram_type": "sequence", "title": "Patch Self Loop Test"},
        "actors": [{"id": "actor_user", "name": "User"}],
        "business_capabilities": [{"id": "cap_analysis", "name": "Analysis Engine"}],
        "participants": ["actor_user", "cap_analysis"],
        "relationships": [
            {"source_id": "actor_user", "target_id": "cap_analysis", "direction": "->", "label": "Start"},
            {"source_id": "cap_analysis", "target_id": "cap_analysis", "direction": "->", "label": "Internal Work"}
        ]
    }

    diagram = SequenceDiagramCanonical.model_validate(data)
    patch = TargetedRepairPatch()

    repaired_diagram = TargetedPatcher.apply_patch(diagram, patch)
    rel_pairs = [(r.source_id, r.target_id) for r in repaired_diagram.relationships]

    assert ("cap_analysis", "cap_analysis") not in rel_pairs
    assert ("actor_user", "cap_analysis") in rel_pairs
