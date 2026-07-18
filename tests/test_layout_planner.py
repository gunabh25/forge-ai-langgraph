"""Unit tests for Layout Planner."""

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
from agents.uml_generator.layout_planner import LayoutPlanner, PlannedComponentLayout, PlannedSequenceLayout


def test_plan_component_layout():
    """Test component layout planning for direction, package order, and formatted arrows."""
    diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Order Flow"),
        actors=[Actor(id="actor_user", name="User")],
        business_packages=[
            BusinessPackage(id="pkg_core", name="Core Package", capability_ids=["cap_order"])
        ],
        business_capabilities=[BusinessCapability(id="cap_order", name="Order Service")],
        databases=[Database(id="db_main", name="Main DB")],
        relationships=[
            Relationship(source_id="actor_user", target_id="cap_order", direction="-->", label="Create Order"),
            Relationship(source_id="cap_order", target_id="db_main", direction="-->", label="Save"),
        ],
    )
    _, layout = LayoutPlanner.plan(diagram)
    assert isinstance(layout, PlannedComponentLayout)
    assert "pkg_core" in layout.package_order
    # Database arrow should be planned downward (-down->)
    assert layout.formatted_arrows[("cap_order", "db_main")] == "-down->"


def test_plan_sequence_layout():
    """Test sequence layout planning for participant order and relationship step sorting."""
    diagram = SequenceDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="sequence", title="Auth Sequence"),
        actors=[Actor(id="actor_user", name="User")],
        business_capabilities=[BusinessCapability(id="cap_auth", name="Auth Service")],
        databases=[Database(id="db_session", name="Session DB")],
        relationships=[
            Relationship(source_id="cap_auth", target_id="db_session", direction="->", label="Validate Token", step_number=2),
            Relationship(source_id="actor_user", target_id="cap_auth", direction="->", label="Login", step_number=1),
        ],
    )
    _, layout = LayoutPlanner.plan(diagram)
    assert isinstance(layout, PlannedSequenceLayout)
    # Left-to-right participant order: actor -> capability -> database
    assert layout.participant_order == ["actor_user", "cap_auth", "db_session"]
    # Ordered relationships by step_number
    assert layout.ordered_relationships[0].step_number == 1
    assert layout.ordered_relationships[1].step_number == 2
