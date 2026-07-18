"""Unit tests for Deterministic PlantUML Builders and Factory."""

from schemas.canonical_diagram import (
    Actor,
    ExternalSystem,
    BusinessCapability,
    Database,
    BusinessPackage,
    Relationship,
    DiagramMetadata,
    ComponentDiagramCanonical,
    SequenceDiagramCanonical,
)
from agents.uml_generator.plantuml_builder import (
    PlantUMLBuilderFactory,
    ComponentPlantUMLBuilder,
    SequencePlantUMLBuilder,
)


def test_builder_factory_resolution():
    """Test resolving per-diagram builders via PlantUMLBuilderFactory."""
    comp_builder = PlantUMLBuilderFactory.get_builder("component")
    seq_builder = PlantUMLBuilderFactory.get_builder("sequence")

    assert isinstance(comp_builder, ComponentPlantUMLBuilder)
    assert isinstance(seq_builder, SequencePlantUMLBuilder)


def test_component_plantuml_builder():
    """Test deterministic PlantUML string compilation for Component Diagram."""
    diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="E-Commerce Architecture"),
        actors=[Actor(id="actor_cust", name="Customer")],
        business_packages=[
            BusinessPackage(id="pkg_order", name="Order Domain", capability_ids=["cap_order_svc"])
        ],
        business_capabilities=[BusinessCapability(id="cap_order_svc", name="Order Service")],
        databases=[Database(id="db_orders", name="Orders DB", db_type="PostgreSQL")],
        relationships=[
            Relationship(source_id="actor_cust", target_id="cap_order_svc", direction="-->", label="Places Order"),
            Relationship(source_id="cap_order_svc", target_id="db_orders", direction="-->", label="Persists Data"),
        ],
    )
    builder = PlantUMLBuilderFactory.get_builder("component")
    puml = builder.build(diagram)

    assert puml.startswith("@startuml")
    assert puml.endswith("@enduml")
    assert 'package "Order Domain" as pkg_order {' in puml
    assert 'component "Order Service" as cap_order_svc' in puml
    assert 'actor "Customer" as actor_cust' in puml
    assert 'database "Orders DB" as db_orders <<PostgreSQL>>' in puml
    assert "actor_cust" in puml
    assert "cap_order_svc" in puml
    assert "db_orders" in puml
    assert "Places Order" in puml


def test_character_for_character_determinism():
    """Test that two canonical diagrams with identical data produce 100% identical byte-for-byte output."""
    diagram1 = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="System Arch"),
        actors=[Actor(id="actor_b", name="User B"), Actor(id="actor_a", name="User A")],
        business_packages=[
            BusinessPackage(id="pkg_z", name="Z Domain", capability_ids=["cap_z"]),
            BusinessPackage(id="pkg_a", name="A Domain", capability_ids=["cap_a"]),
        ],
        business_capabilities=[
            BusinessCapability(id="cap_z", name="Service Z"),
            BusinessCapability(id="cap_a", name="Service A"),
        ],
        databases=[
            Database(id="db_2", name="DB 2"),
            Database(id="db_1", name="DB 1"),
        ],
        relationships=[
            Relationship(source_id="cap_z", target_id="db_2", direction="-->", label="Rel 2"),
            Relationship(source_id="actor_a", target_id="cap_a", direction="-->", label="Rel 1"),
        ],
    )

    diagram2 = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="System Arch"),
        actors=[Actor(id="actor_a", name="User A"), Actor(id="actor_b", name="User B")],
        business_packages=[
            BusinessPackage(id="pkg_a", name="A Domain", capability_ids=["cap_a"]),
            BusinessPackage(id="pkg_z", name="Z Domain", capability_ids=["cap_z"]),
        ],
        business_capabilities=[
            BusinessCapability(id="cap_a", name="Service A"),
            BusinessCapability(id="cap_z", name="Service Z"),
        ],
        databases=[
            Database(id="db_1", name="DB 1"),
            Database(id="db_2", name="DB 2"),
        ],
        relationships=[
            Relationship(source_id="actor_a", target_id="cap_a", direction="-->", label="Rel 1"),
            Relationship(source_id="cap_z", target_id="db_2", direction="-->", label="Rel 2"),
        ],
    )

    builder = PlantUMLBuilderFactory.get_builder("component")
    out1 = builder.build(diagram1)
    out2 = builder.build(diagram2)

    assert out1 == out2, "PlantUML Builder output must be 100% character-for-character identical regardless of input key order"


def test_hidden_alignment_edge_generation():
    """Test that hidden alignment edges are generated for spatial grid layout."""
    diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Grid Layout"),
        business_packages=[
            BusinessPackage(id="pkg_auth", name="Auth Domain", capability_ids=["cap_auth"]),
            BusinessPackage(id="pkg_billing", name="Billing Domain", capability_ids=["cap_billing"]),
        ],
        business_capabilities=[
            BusinessCapability(id="cap_auth", name="Auth Service"),
            BusinessCapability(id="cap_billing", name="Billing Service"),
        ],
        databases=[
            Database(id="db_auth", name="Auth DB"),
            Database(id="db_billing", name="Billing DB"),
        ],
    )
    builder = PlantUMLBuilderFactory.get_builder("component")
    puml = builder.build(diagram)

    assert "' Layout Alignment Directives" in puml
    assert "-[hidden]" in puml


def test_sequence_plantuml_builder():
    """Test deterministic PlantUML string compilation for Sequence Diagram."""
    diagram = SequenceDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="sequence", title="Order Fulfillment"),
        actors=[Actor(id="actor_cust", name="Customer")],
        business_capabilities=[BusinessCapability(id="cap_order_svc", name="Order Service")],
        databases=[Database(id="db_orders", name="Orders DB")],
        participants=["actor_cust", "cap_order_svc", "db_orders"],
        relationships=[
            Relationship(source_id="actor_cust", target_id="cap_order_svc", direction="->", label="Submit Order", step_number=1),
            Relationship(source_id="cap_order_svc", target_id="db_orders", direction="->", label="Insert Record", step_number=2),
        ],
    )
    builder = PlantUMLBuilderFactory.get_builder("sequence")
    puml = builder.build(diagram)

    assert "@startuml" in puml
    assert "@enduml" in puml
    assert "autonumber" in puml
    assert 'actor "Customer" as actor_cust' in puml
    assert 'participant "Order Service" as cap_order_svc' in puml
    assert 'database "Orders DB" as db_orders' in puml
    assert "actor_cust -> cap_order_svc : Submit Order" in puml
    assert "cap_order_svc -> db_orders : Insert Record" in puml
