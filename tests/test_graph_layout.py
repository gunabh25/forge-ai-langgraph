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
from agents.uml_generator.graph_model import DirectedGraph
from agents.uml_generator.layer_assignment import LayerAssigner
from agents.uml_generator.crossing_optimizer import CrossingOptimizer
from agents.uml_generator.node_ordering import NodeOrderer
from agents.uml_generator.coordinate_assignment import CoordinateAssigner
from agents.uml_generator.edge_router import EdgeRouter


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
    """Test that CrossingOptimizer produces a layout with minimal cost."""
    graph = DirectedGraph(complex_diagram)
    LayerAssigner.assign_layers(graph)
    
    layers = {i: graph.get_layer_nodes(i) for i in range(graph.max_layer + 1)}
    baseline_crossings = CrossingOptimizer.count_crossings(graph, layers)
    
    CrossingOptimizer.optimize_crossings(graph)
    
    layers = {i: graph.get_layer_nodes(i) for i in range(graph.max_layer + 1)}
    optimized_crossings = CrossingOptimizer.count_crossings(graph, layers)
    
    assert optimized_crossings <= baseline_crossings


def test_database_placement_layer(complex_diagram: ComponentDiagramCanonical):
    """Test that databases are correctly positioned relative to their capability (Phase 9.13)."""
    optimized_result = DeterministicLayoutEngine.compute_component_layout(complex_diagram)
    layers = optimized_result.layers
    
    assert "db_main" in layers.layer_4_databases
    assert "db_analytics" in layers.layer_4_databases
    
    # Verify databases are placed strictly below their owner
    cap_a_layer = layers.element_layer_map["cap_a"]
    db_main_layer = layers.element_layer_map["db_main"]
    assert db_main_layer == cap_a_layer + 1
    
    cap_d_layer = layers.element_layer_map["cap_d"]
    db_analytics_layer = layers.element_layer_map["db_analytics"]
    assert db_analytics_layer == cap_d_layer + 1


def test_external_system_optimization(complex_diagram: ComponentDiagramCanonical):
    """Test that external systems are dynamically assigned based on flow (Phase 9.13)."""
    optimized_result = DeterministicLayoutEngine.compute_component_layout(complex_diagram)
    layers = optimized_result.layers
    
    # ext_ingest should be Layer 1 (Left) because it receives traffic from Actor (Layer 0)
    assert layers.element_layer_map["ext_ingest"] == 1
    
    # ext_downstream should be placed at the very end (max layer)
    ext_layer = layers.element_layer_map["ext_downstream"]
    all_layers = layers.element_layer_map.values()
    max_l = max(all_layers)
    assert ext_layer == max_l

