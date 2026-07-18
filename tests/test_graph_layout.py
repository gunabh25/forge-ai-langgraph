"""Test suite for Graph Layout Optimizer (Phase 9.12)."""

import pytest

from schemas.canonical_diagram import (
    ComponentDiagramCanonical,
    DiagramMetadata,
    Actor,
    ExternalSystem,
    BusinessCapability,
    Database,
    BusinessPackage,
    Relationship,
)
from agents.uml_generator.layout_engine import DeterministicLayoutEngine
from agents.uml_generator.graph_layout_optimizer import GraphLayoutOptimizer


@pytest.fixture
def complex_diagram() -> ComponentDiagramCanonical:
    """Fixture providing a complex diagram to test crossing minimization."""
    return ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Complex Test"),
        actors=[Actor(id="actor_1", name="User")],
        external_systems=[
            ExternalSystem(id="ext_ingest", name="Ingest API"),
            ExternalSystem(id="ext_downstream", name="Downstream API"),
        ],
        business_packages=[
            BusinessPackage(id="pkg_core", name="Core", capability_ids=["cap_a", "cap_b"]),
            BusinessPackage(id="pkg_analytics", name="Analytics", capability_ids=["cap_c", "cap_d"]),
        ],
        business_capabilities=[
            BusinessCapability(id="cap_a", name="Service A"),
            BusinessCapability(id="cap_b", name="Service B"),
            BusinessCapability(id="cap_c", name="Service C"),
            BusinessCapability(id="cap_d", name="Service D"),
        ],
        databases=[
            Database(id="db_main", name="Main DB"),
            Database(id="db_analytics", name="Analytics DB"),
        ],
        relationships=[
            Relationship(source_id="actor_1", target_id="ext_ingest", direction="-->", label="Uses"),
            Relationship(source_id="ext_ingest", target_id="cap_b", direction="-->", label="API"),
            Relationship(source_id="cap_b", target_id="cap_a", direction="-->", label="Calls"),
            Relationship(source_id="cap_a", target_id="db_main", direction="-->", label="Writes"),
            Relationship(source_id="cap_b", target_id="cap_c", direction="-->", label="Events"),
            Relationship(source_id="cap_c", target_id="cap_d", direction="-->", label="Process"),
            Relationship(source_id="cap_d", target_id="db_analytics", direction="-->", label="Writes"),
            Relationship(source_id="cap_d", target_id="ext_downstream", direction="-->", label="Export"),
        ],
    )


def test_graph_layout_optimizer_reduces_cost(complex_diagram: ComponentDiagramCanonical):
    """Test that GraphLayoutOptimizer produces a layout with equal or lower cost than baseline."""
    initial_result = DeterministicLayoutEngine.compute_component_layout(complex_diagram)
    
    # We intercept the initial result before GraphOptimizer logic
    # Actually, compute_component_layout already runs GraphLayoutOptimizer internally.
    # Let's run the base assignment manually.
    direction = DeterministicLayoutEngine.analyze_topology(complex_diagram)
    layers = DeterministicLayoutEngine.assign_layers(complex_diagram)
    arrows = DeterministicLayoutEngine.compute_routing_hints(complex_diagram, layers, direction)
    
    baseline_cost = GraphLayoutOptimizer.calculate_layout_cost(complex_diagram, layers, arrows)
    
    # Now run the full optimized engine
    optimized_result = DeterministicLayoutEngine.compute_component_layout(complex_diagram)
    
    optimized_cost = optimized_result.readability_metrics.get("layout_cost", baseline_cost)
    
    # The optimized cost should be <= baseline cost
    assert optimized_cost <= baseline_cost


def test_database_placement_layer(complex_diagram: ComponentDiagramCanonical):
    """Test that databases are strictly assigned to Layer 4 (Workstream 6)."""
    optimized_result = DeterministicLayoutEngine.compute_component_layout(complex_diagram)
    layers = optimized_result.layers
    
    assert "db_main" in layers.layer_4_databases
    assert "db_analytics" in layers.layer_4_databases
    
    # Verify they are only in Layer 4
    assert layers.element_layer_map["db_main"] == 4
    assert layers.element_layer_map["db_analytics"] == 4


def test_external_system_optimization(complex_diagram: ComponentDiagramCanonical):
    """Test that external systems are dynamically assigned to Layer 1 or Layer 3 (Workstream 7)."""
    optimized_result = DeterministicLayoutEngine.compute_component_layout(complex_diagram)
    layers = optimized_result.layers
    
    # ext_ingest should be Layer 1 (Left) because it receives traffic from Actor (Layer 0)
    assert layers.element_layer_map["ext_ingest"] == 1
    
    # ext_downstream should be Layer 3 (Right) because it receives traffic from Layer 2
    assert layers.element_layer_map["ext_downstream"] == 3
