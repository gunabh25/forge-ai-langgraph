"""Layout Planner.

Sits between Canonical Diagram JSON validation and the PlantUML builder.
Delegates spatial placement, topology analysis, layer routing, and hidden alignment edges
to DeterministicLayoutEngine.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from schemas.canonical_diagram import (
    BaseCanonicalDiagram,
    ComponentDiagramCanonical,
    SequenceDiagramCanonical,
    Relationship,
)
from agents.uml_generator.layout_engine import DeterministicLayoutEngine
from config.logging import get_logger

logger = get_logger("agents.uml_generator.layout_planner")


# ---------------------------------------------------------------------------
# Layout Plan Data Models
# ---------------------------------------------------------------------------

class PlannedComponentLayout(BaseModel):
    """Layout metadata for Component Diagrams."""
    direction_directive: str = Field("top to bottom direction", description="Layout orientation directive")
    skinparams: List[str] = Field(
        default_factory=lambda: [
            "skinparam componentStyle uml2",
            "skinparam shadowing false",
            "skinparam packageStyle rectangle",
            "skinparam linetype ortho",
        ]
    )
    package_order: List[str] = Field(default_factory=list, description="Ordered package IDs")
    standalone_element_order: List[str] = Field(default_factory=list, description="Ordered standalone element IDs")
    formatted_arrows: Dict[Tuple[str, str], str] = Field(
        default_factory=dict,
        description="Map of (source_id, target_id) -> formatted PlantUML arrow string (e.g. '-down->', '-right->')"
    )
    hidden_alignment_edges: List[str] = Field(
        default_factory=list,
        description="List of hidden alignment edge strings (e.g. 'pkg_1 -[hidden]right-> pkg_2')"
    )


class PlannedSequenceLayout(BaseModel):
    """Layout metadata for Sequence Diagrams."""
    autonumber: bool = True
    skinparams: List[str] = Field(
        default_factory=lambda: [
            "skinparam responseMessageBelowArrow true",
            "skinparam maxMessageSize 200",
            "skinparam shadowing false",
        ]
    )
    participant_order: List[str] = Field(
        default_factory=list,
        description="Ordered list of element IDs for left-to-right sequence lifelines"
    )
    ordered_relationships: List[Relationship] = Field(
        default_factory=list,
        description="Relationships sorted strictly by step_number or appearance"
    )


# ---------------------------------------------------------------------------
# Layout Planner Implementation
# ---------------------------------------------------------------------------

class LayoutPlanner:
    """Computes layout directives and structural ordering for canonical diagrams."""

    @staticmethod
    def plan_component_layout(diagram: ComponentDiagramCanonical) -> PlannedComponentLayout:
        """Compute layout plan for Component Diagram via DeterministicLayoutEngine."""
        res = DeterministicLayoutEngine.compute_component_layout(diagram)

        layout = PlannedComponentLayout(
            direction_directive=res.direction_directive,
            package_order=res.layers.layer_2_packages,
            standalone_element_order=res.layers.layer_2_capabilities,
            formatted_arrows=res.formatted_arrows,
            hidden_alignment_edges=res.hidden_alignment_edges,
        )
        if res.dynamic_skinparams:
            layout.skinparams.extend(res.dynamic_skinparams)
        return layout

    @staticmethod
    def plan_sequence_layout(diagram: SequenceDiagramCanonical) -> PlannedSequenceLayout:
        """Compute layout plan for Sequence Diagram."""
        # 1. Determine participant order left-to-right:
        #    Actors -> External Systems -> Business Capabilities -> Databases
        if diagram.participants:
            all_ids = diagram.all_element_ids()
            ordered_participant_ids = [p_id for p_id in diagram.participants if p_id in all_ids]
            missing = sorted([e.id for e in diagram.all_elements() if e.id not in set(ordered_participant_ids)])
            ordered_participant_ids.extend(missing)
        else:
            actors = sorted([e.id for e in diagram.actors])
            ext_systems = sorted([e.id for e in diagram.external_systems])
            capabilities = sorted([e.id for e in diagram.business_capabilities])
            databases = sorted([e.id for e in diagram.databases])
            ordered_participant_ids = actors + ext_systems + capabilities + databases

        # 2. Order relationships deterministically by step_number or source_id/target_id
        rels = list(diagram.relationships)
        if any(r.step_number is not None for r in rels):
            rels.sort(key=lambda r: (r.step_number if r.step_number is not None else 9999, r.source_id, r.target_id))
        else:
            rels.sort(key=lambda r: (r.source_id, r.target_id))

        return PlannedSequenceLayout(
            participant_order=ordered_participant_ids,
            ordered_relationships=rels,
        )

    @classmethod
    def plan(cls, diagram: BaseCanonicalDiagram) -> Tuple[BaseCanonicalDiagram, BaseModel]:
        """Entry point to compute layout plan for any canonical diagram."""
        if isinstance(diagram, ComponentDiagramCanonical):
            layout = cls.plan_component_layout(diagram)
        elif isinstance(diagram, SequenceDiagramCanonical):
            layout = cls.plan_sequence_layout(diagram)
        else:
            if hasattr(diagram, "business_packages"):
                layout = cls.plan_component_layout(diagram)  # type: ignore[arg-type]
            else:
                layout = cls.plan_sequence_layout(diagram)  # type: ignore[arg-type]

        return diagram, layout
