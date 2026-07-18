"""Unit tests for Targeted Repair and Patch Application."""

from schemas.canonical_diagram import (
    Actor,
    BusinessCapability,
    Database,
    BusinessPackage,
    Relationship,
    DiagramMetadata,
    ComponentDiagramCanonical,
)
from agents.uml_repair.targeted_patcher import TargetedPatcher, TargetedRepairPatch


def test_targeted_patch_parsing():
    """Test parsing TargetedRepairPatch from JSON string."""
    patch_json = """
    {
        "repaired_aliases": {"cap_order": "Updated Order Service"},
        "repaired_relationships": [
            {"source_id": "cap_order", "target_id": "db_order", "direction": "-->", "label": "Persist Order"}
        ],
        "removed_participant_ids": ["cap_illegal_service"]
    }
    """
    patch = TargetedPatcher.parse_patch_from_response(patch_json)
    assert patch.repaired_aliases == {"cap_order": "Updated Order Service"}
    assert patch.repaired_relationships is not None
    assert len(patch.repaired_relationships) == 1
    assert patch.repaired_relationships[0].label == "Persist Order"
    assert patch.removed_participant_ids == ["cap_illegal_service"]


def test_apply_patch_to_component_diagram():
    """Test merging TargetedRepairPatch into ComponentDiagramCanonical."""
    diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Original System"),
        actors=[Actor(id="actor_user", name="User")],
        business_capabilities=[
            BusinessCapability(id="cap_order", name="Old Order Name"),
            BusinessCapability(id="cap_illegal", name="Illegal Service"),
        ],
        databases=[Database(id="db_order", name="Order DB")],
        relationships=[
            Relationship(source_id="actor_user", target_id="cap_order", direction="-->", label="Old Rel"),
        ],
    )

    patch = TargetedRepairPatch(
        repaired_aliases={"cap_order": "Renamed Order Service"},
        removed_participant_ids=["cap_illegal"],
        repaired_relationships=[
            Relationship(source_id="actor_user", target_id="cap_order", direction="-->", label="New Rel"),
            Relationship(source_id="cap_order", target_id="db_order", direction="-->", label="Save Order"),
        ],
    )

    updated_diagram = TargetedPatcher.apply_patch(diagram, patch)

    # 1. Verify unapproved service was removed
    element_ids = updated_diagram.all_element_ids()
    assert "cap_illegal" not in element_ids
    assert "cap_order" in element_ids

    # 2. Verify display name was repaired
    order_cap = updated_diagram.get_element_by_id("cap_order")
    assert order_cap is not None
    assert order_cap.name == "Renamed Order Service"

    # 3. Verify relationships were updated
    assert len(updated_diagram.relationships) == 2
    labels = {r.label for r in updated_diagram.relationships}
    assert "Save Order" in labels
