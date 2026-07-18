"""Test suite for Phase 9.8 Visual Layout Optimization (Presentation Only)."""

import pytest
from schemas.canonical_diagram import ComponentDiagramCanonical
from agents.uml_generator.layout_engine import DeterministicLayoutEngine
from agents.uml_generator.layout_planner import LayoutPlanner
from agents.uml_generator.plantuml_builder import PlantUMLBuilderFactory


@pytest.fixture
def sample_component_diagram():
    return ComponentDiagramCanonical.model_validate({
        "metadata": {"diagram_type": "component", "title": "Visual Layout Test System"},
        "actors": [{"id": "actor_user", "name": "User"}],
        "external_systems": [{"id": "ext_sebi", "name": "SEBI System"}],
        "business_packages": [
            {
                "id": "pkg_compliance",
                "name": "Compliance Core",
                "capability_ids": [
                    "cap_impact_assessment",
                    "cap_circular_ingestion",
                    "cap_document_parsing",
                    "cap_requirement_extraction",
                    "cap_gap_analysis"
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


def test_spatial_layer_hierarchy(sample_component_diagram):
    """Verify elements are assigned to strict spatial layers (Layer 0, 1, 2, 4)."""
    layers = DeterministicLayoutEngine.assign_layers(sample_component_diagram)

    assert layers.element_layer_map["actor_user"] == 0
    assert layers.element_layer_map["ext_sebi"] == 1
    assert layers.element_layer_map["pkg_compliance"] == 2
    assert layers.element_layer_map["cap_circular_ingestion"] == 2
    assert layers.element_layer_map["db_compliance"] == 4


def test_intra_package_topological_sort(sample_component_diagram):
    """Verify intra-package capabilities are ordered topologically according to flow."""
    pkg_cap_ids = sample_component_diagram.business_packages[0].capability_ids
    sorted_caps = DeterministicLayoutEngine.topological_sort_capabilities(
        sample_component_diagram, pkg_cap_ids
    )

    # Topological order must start with ingestion -> parsing -> extraction -> gap -> impact
    assert sorted_caps.index("cap_circular_ingestion") < sorted_caps.index("cap_document_parsing")
    assert sorted_caps.index("cap_document_parsing") < sorted_caps.index("cap_requirement_extraction")
    assert sorted_caps.index("cap_requirement_extraction") < sorted_caps.index("cap_gap_analysis")
    assert sorted_caps.index("cap_gap_analysis") < sorted_caps.index("cap_impact_assessment")


def test_dynamic_spacing_skinparams(sample_component_diagram):
    """Verify dynamic nodesep, ranksep, padding, and arrow thickness are calculated."""
    res = DeterministicLayoutEngine.compute_component_layout(sample_component_diagram)
    assert any("skinparam nodesep" in s for s in res.dynamic_skinparams)
    assert any("skinparam ranksep" in s for s in res.dynamic_skinparams)
    assert any("skinparam ArrowThickness 1.5" in s for s in res.dynamic_skinparams)


def test_builder_emits_topological_package_ordering(sample_component_diagram):
    """Verify PlantUML builder renders capabilities inside packages in topological order."""
    builder = PlantUMLBuilderFactory.get_builder("component")
    puml = builder.build(sample_component_diagram)

    assert puml.index("cap_circular_ingestion") < puml.index("cap_document_parsing")
    assert puml.index("cap_document_parsing") < puml.index("cap_requirement_extraction")
    assert puml.index("cap_requirement_extraction") < puml.index("cap_gap_analysis")
    assert puml.index("cap_gap_analysis") < puml.index("cap_impact_assessment")


def test_presentation_readability_metrics(sample_component_diagram):
    """Verify presentation readability metrics are computed."""
    res = DeterministicLayoutEngine.compute_component_layout(sample_component_diagram)
    metrics = res.readability_metrics

    assert metrics["package_compactness"] == 1.0
    assert metrics["backward_edges"] == 0
    assert metrics["total_relationships"] == 7
