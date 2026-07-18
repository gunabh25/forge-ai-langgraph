"""Tests for the layout contract between LayoutPlanner and PlantUMLBuilder."""

import pytest
from pydantic import BaseModel

from schemas.canonical_diagram import (
    ComponentDiagramCanonical,
    DiagramMetadata,
    Actor,
    BusinessCapability,
)
from agents.uml_generator.layout_planner import LayoutPlanner, PlannedComponentLayout
from agents.uml_generator.plantuml_builder import (
    ComponentPlantUMLBuilder,
    LayoutContractError,
)

@pytest.fixture
def minimal_diagram():
    return ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Test"),
        actors=[Actor(id="actor_1", name="User")],
        business_capabilities=[BusinessCapability(id="cap_1", name="Service")],
    )

def test_planner_returns_valid_contract(minimal_diagram):
    """Verify LayoutPlanner produces exactly a PlannedComponentLayout."""
    layout = LayoutPlanner.plan_component_layout(minimal_diagram)
    
    assert isinstance(layout, PlannedComponentLayout)
    assert hasattr(layout, "direction_directive")
    assert hasattr(layout, "skinparams")
    assert hasattr(layout, "standalone_element_order")
    assert hasattr(layout, "formatted_arrows")
    assert hasattr(layout, "hidden_alignment_edges")
    assert not hasattr(layout, "dynamic_skinparams")  # Should be totally gone


def test_builder_consumes_valid_contract_successfully(minimal_diagram):
    """Verify ComponentPlantUMLBuilder correctly consumes the formal layout contract."""
    layout = LayoutPlanner.plan_component_layout(minimal_diagram)
    builder = ComponentPlantUMLBuilder()
    
    # Should not raise any LayoutContractError
    puml = builder.build(minimal_diagram, layout=layout)
    assert "@startuml" in puml
    assert "top to bottom direction" in puml or "left to right direction" in puml


def test_builder_raises_contract_error_on_mismatch(minimal_diagram):
    """Verify ComponentPlantUMLBuilder raises a descriptive LayoutContractError on mismatch."""
    class BadLayout(BaseModel):
        # Missing standalone_element_order, formatted_arrows, etc.
        direction_directive: str = "top to bottom direction"
        skinparams: list = []

    bad_layout = BadLayout()
    builder = ComponentPlantUMLBuilder()

    with pytest.raises(LayoutContractError) as exc_info:
        builder.build(minimal_diagram, layout=bad_layout)

    # Check for helpful error text
    error_msg = str(exc_info.value)
    assert "Missing layout attribute" in error_msg
    assert "Expected by:\nComponentPlantUMLBuilder" in error_msg
    assert "Produced by:\nLayoutPlanner" in error_msg
    assert "Suggested Fix:\nSynchronize layout contract." in error_msg
