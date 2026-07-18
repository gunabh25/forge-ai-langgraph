"""Unit tests for Deterministic Layout Engine."""

from schemas.canonical_diagram import (
    Actor,
    ExternalSystem,
    BusinessCapability,
    Database,
    BusinessPackage,
    Relationship,
    DiagramMetadata,
    ComponentDiagramCanonical,
)
from agents.uml_generator.layout_engine import (
    DeterministicLayoutEngine,
    EngineLayoutResult,
    LayerAssignment,
)


def test_topology_analysis_orientation():
    """Test topology analysis chooses direction based on diagram breadth and node count."""
    # Small diagram -> Top to bottom direction
    small_diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Small App"),
        actors=[Actor(id="actor_user", name="User")],
        business_capabilities=[BusinessCapability(id="cap_app", name="App Service")],
        databases=[Database(id="db_app", name="App DB")],
        relationships=[
            Relationship(source_id="actor_user", target_id="cap_app", direction="-->"),
            Relationship(source_id="cap_app", target_id="db_app", direction="-->"),
        ],
    )
    dir_small = DeterministicLayoutEngine.analyze_topology(small_diagram)
    assert dir_small == "top to bottom direction"

    # Multi-package diagram -> Left to right direction
    large_diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Large System"),
        actors=[Actor(id="actor_cust", name="Customer")],
        business_packages=[
            BusinessPackage(id="pkg_orders", name="Order Domain", capability_ids=["cap_orders"]),
            BusinessPackage(id="pkg_payments", name="Payment Domain", capability_ids=["cap_payments"]),
        ],
        business_capabilities=[
            BusinessCapability(id="cap_orders", name="Order Service"),
            BusinessCapability(id="cap_payments", name="Payment Service"),
        ],
        databases=[
            Database(id="db_orders", name="Orders DB"),
            Database(id="db_payments", name="Payments DB"),
        ],
        relationships=[
            Relationship(source_id="actor_cust", target_id="cap_orders", direction="-->"),
            Relationship(source_id="cap_orders", target_id="cap_payments", direction="-->"),
            Relationship(source_id="cap_orders", target_id="db_orders", direction="-->"),
            Relationship(source_id="cap_payments", target_id="db_payments", direction="-->"),
        ],
    )
    dir_large = DeterministicLayoutEngine.analyze_topology(large_diagram)
    assert dir_large == "left to right direction"


def test_spatial_layer_assignment_rules():
    """Test layer assignment: Actors=0, Ingest Ext=1, Packages/Capabilities=2, Downstream Ext=3, Databases=4."""
    diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="E-Commerce Architecture"),
        actors=[Actor(id="actor_cust", name="Customer")],
        external_systems=[
            ExternalSystem(id="sys_idp", name="Identity Provider"), # Ingest (connected to actor)
            ExternalSystem(id="sys_stripe", name="Stripe API"),    # Downstream (connected to payment cap)
        ],
        business_packages=[
            BusinessPackage(id="pkg_core", name="Core", capability_ids=["cap_order", "cap_pay"])
        ],
        business_capabilities=[
            BusinessCapability(id="cap_order", name="Order Service"),
            BusinessCapability(id="cap_pay", name="Payment Service"),
        ],
        databases=[Database(id="db_orders", name="Orders DB")],
        relationships=[
            Relationship(source_id="actor_cust", target_id="sys_idp", direction="-->"),
            Relationship(source_id="actor_cust", target_id="cap_order", direction="-->"),
            Relationship(source_id="cap_pay", target_id="sys_stripe", direction="-->"),
            Relationship(source_id="cap_order", target_id="db_orders", direction="-->"),
        ],
    )

    layers = DeterministicLayoutEngine.assign_layers(diagram)

    assert layers.element_layer_map["actor_cust"] == 0
    assert layers.element_layer_map["sys_idp"] == 1
    assert layers.element_layer_map["pkg_core"] == 2
    assert layers.element_layer_map["cap_order"] == 2
    assert layers.element_layer_map["sys_stripe"] == 3
    assert layers.element_layer_map["db_orders"] == 4


def test_relationship_routing_hints():
    """Test relationship arrow direction hints computed from layer indices."""
    diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Routing Test"),
        actors=[Actor(id="actor_user", name="User")],
        business_capabilities=[BusinessCapability(id="cap_srv", name="Service")],
        databases=[Database(id="db_main", name="Main DB")],
        relationships=[
            Relationship(source_id="actor_user", target_id="cap_srv", direction="-->"),
            Relationship(source_id="cap_srv", target_id="db_main", direction="-->"),
        ],
    )
    layers = DeterministicLayoutEngine.assign_layers(diagram)
    arrows = DeterministicLayoutEngine.compute_routing_hints(diagram, layers, "left to right direction")

    # Actor -> Capability in LR mode -> -right->
    assert arrows[("actor_user", "cap_srv")] == "-right->"
    # Capability -> Database -> -down->
    assert arrows[("cap_srv", "db_main")] == "-down->"


def test_spatial_alignment_edges():
    """Test hidden alignment edge generation for spatial grid layout."""
    diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Grid Alignment"),
        actors=[Actor(id="actor_user", name="User")],
        business_packages=[
            BusinessPackage(id="pkg_1", name="Pkg 1", capability_ids=["cap_1"]),
            BusinessPackage(id="pkg_2", name="Pkg 2", capability_ids=["cap_2"]),
        ],
        business_capabilities=[
            BusinessCapability(id="cap_1", name="Cap 1"),
            BusinessCapability(id="cap_2", name="Cap 2"),
        ],
        databases=[
            Database(id="db_1", name="DB 1"),
            Database(id="db_2", name="DB 2"),
        ],
    )
    res = DeterministicLayoutEngine.compute_component_layout(diagram)

    assert len(res.hidden_alignment_edges) > 0
    # Package alignment edge
    assert "pkg_1 -[hidden]right-> pkg_2" in res.hidden_alignment_edges or "pkg_1 -[hidden]down-> pkg_2" in res.hidden_alignment_edges
    # Database alignment edge
    assert "db_1 -[hidden]right-> db_2" in res.hidden_alignment_edges
