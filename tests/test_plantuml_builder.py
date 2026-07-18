"""Unit tests for PlantUML Builders and Factory."""

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
    assert puml.endswith("@enumdl") or "@startuml" in puml and "@enduml" in puml
    assert 'package "Order Domain"' in puml
    assert 'component "Order Service" as cap_order_svc' in puml
    assert 'actor "Customer" as actor_cust' in puml
    assert 'database "Orders DB" as db_orders <<PostgreSQL>>' in puml
    assert "actor_cust" in puml
    assert "cap_order_svc" in puml
    assert "db_orders" in puml
    assert "Places Order" in puml


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
