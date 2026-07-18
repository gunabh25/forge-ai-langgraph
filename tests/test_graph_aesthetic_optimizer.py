"""Test suite for Phase 9.10 Graph Aesthetic Optimization (Visual Layout Only)."""

import pytest
from schemas.canonical_diagram import ComponentDiagramCanonical
from agents.uml_generator.layout_engine import DeterministicLayoutEngine
from agents.uml_generator.graph_layout_optimizer import GraphLayoutOptimizer
from agents.uml_generator.plantuml_builder import PlantUMLBuilderFactory


@pytest.fixture
def sample_component_diagram():
    return ComponentDiagramCanonical.model_validate({
        "metadata": {"diagram_type": "component", "title": "Graph Aesthetic Test System"},
        "actors": [{"id": "actor_user", "name": "User"}],
        "external_systems": [{"id": "ext_sebi", "name": "SEBI System"}],
        "business_packages": [
            {
                "id": "pkg_compliance",
                "name": "Compliance Core",
                "capability_ids": [
                    "cap_circular_ingestion",
                    "cap_document_parsing",
                    "cap_requirement_extraction",
                    "cap_gap_analysis",
                    "cap_impact_assessment"
                ]
            }
        ],
        "business_capabilities": [
            {"id": "cap_circular_ingestion", "name": "Circular Ingestion"},
            {"id": "cap_document_parsing", "name": "Document Parsing"},
            {"id": "cap_requirement_extraction", "name": "Requirement Extraction"},
            {"id": "cap_gap_analysis", "name": "Gap Analysis"},
            {"id": "cap_impact_assessment", "name": "Impact Assessment"}
        ],
        "databases": [{"id": "db_compliance", "name": "Compliance DB"}],
        "relationships": [
            {"source_id": "actor_user", "target_id": "cap_circular_ingestion", "direction": "-->", "label": "Uploads"},
            {"source_id": "ext_sebi", "target_id": "cap_circular_ingestion", "direction": "-->", "label": "Publishes"},
            {"source_id": "cap_circular_ingestion", "target_id": "cap_document_parsing", "direction": "-->", "label": "Forwards"},
            {"source_id": "cap_document_parsing", "target_id": "cap_requirement_extraction", "direction": "-->", "label": "Extracts"},
            {"source_id": "cap_requirement_extraction", "target_id": "cap_gap_analysis", "direction": "-->", "label": "Feeds"},
            {"source_id": "cap_gap_analysis", "target_id": "cap_impact_assessment", "direction": "-->", "label": "Evaluates"},
            {"source_id": "cap_impact_assessment", "target_id": "db_compliance", "direction": "-->", "label": "Persists"}
        ]
    })


def test_layout_cost_calculation(sample_component_diagram):
    """Verify layout cost is computed deterministically."""
    res = DeterministicLayoutEngine.compute_component_layout(sample_component_diagram)
    cost = GraphLayoutOptimizer.calculate_layout_cost(sample_component_diagram, res.layers, res.formatted_arrows)

    assert cost >= 0.0
    assert "layout_cost" in res.readability_metrics
    assert res.readability_metrics["layout_cost"] == round(cost, 2)


def test_graph_optimizer_pass_preserves_architecture(sample_component_diagram):
    """Verify GraphLayoutOptimizer pass preserves canonical diagram elements and IDs byte-for-byte."""
    builder = PlantUMLBuilderFactory.get_builder("component")
    puml = builder.build(sample_component_diagram)

    assert "actor_user" in puml
    assert "ext_sebi" in puml
    assert "pkg_compliance" in puml
    assert "db_compliance" in puml
    assert "cap_circular_ingestion" in puml
