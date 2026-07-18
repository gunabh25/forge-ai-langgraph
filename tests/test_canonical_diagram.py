"""Unit tests for Canonical Diagram Schemas and Validator."""

import pytest
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
from agents.uml_generator.canonical_validator import (
    CanonicalDiagramValidator,
    CanonicalValidationError,
)
from core.business_normalizer import normalize_name


def test_component_diagram_canonical_schema():
    """Test valid ComponentDiagramCanonical model creation."""
    diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Order System"),
        actors=[Actor(id="actor_customer", name="Customer")],
        external_systems=[ExternalSystem(id="sys_payment", name="Payment Gateway", technology="REST")],
        business_packages=[
            BusinessPackage(id="pkg_core", name="Core Services", capability_ids=["cap_order_service"])
        ],
        business_capabilities=[BusinessCapability(id="cap_order_service", name="Order Service")],
        databases=[Database(id="db_order_db", name="Order DB", db_type="PostgreSQL")],
        relationships=[
            Relationship(source_id="actor_customer", target_id="cap_order_service", direction="-->", label="Place Order"),
            Relationship(source_id="cap_order_service", target_id="db_order_db", direction="-->", label="Store Order"),
        ],
    )
    assert diagram.metadata.diagram_type == "component"
    assert "actor_customer" in diagram.all_element_ids()
    assert "cap_order_service" in diagram.all_element_ids()
    assert "db_order_db" in diagram.all_element_ids()
    assert "sys_payment" in diagram.all_element_ids()


def test_sequence_diagram_canonical_schema():
    """Test valid SequenceDiagramCanonical model creation."""
    diagram = SequenceDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="sequence", title="Order Sequence"),
        actors=[Actor(id="actor_customer", name="Customer")],
        business_capabilities=[BusinessCapability(id="cap_order_service", name="Order Service")],
        databases=[Database(id="db_order_db", name="Order DB")],
        participants=["actor_customer", "cap_order_service", "db_order_db"],
        relationships=[
            Relationship(source_id="actor_customer", target_id="cap_order_service", direction="->", label="Place Order", step_number=1),
            Relationship(source_id="cap_order_service", target_id="db_order_db", direction="->", label="Persist Order", step_number=2),
        ],
    )
    assert diagram.metadata.diagram_type == "sequence"
    assert len(diagram.participants) == 3
    assert len(diagram.relationships) == 2


def test_validator_reference_integrity():
    """Test validator catches invalid stable ID references."""
    invalid_diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Invalid References"),
        actors=[Actor(id="actor_customer", name="Customer")],
        relationships=[
            Relationship(source_id="actor_customer", target_id="non_existent_id", direction="-->", label="Broken")
        ],
    )
    with pytest.raises(CanonicalValidationError) as exc_info:
        CanonicalDiagramValidator.validate_references(invalid_diagram)
    assert "non_existent_id" in str(exc_info.value)


def test_validator_traceability_check():
    """Test validator catches unapproved business capabilities."""
    diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Traceability Test"),
        business_capabilities=[
            BusinessCapability(id="cap_auth", name="Authentication Service"),
            BusinessCapability(id="cap_invented", name="Magic Unapproved Service"),
        ],
    )
    allowed = {normalize_name("Authentication Service")}
    hallucinated = CanonicalDiagramValidator.validate_traceability(diagram, allowed)
    assert "Magic Unapproved Service" in hallucinated
    assert "Authentication Service" not in hallucinated
