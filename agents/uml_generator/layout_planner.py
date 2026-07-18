"""Layout Planner.

Sits between Canonical Diagram JSON validation and the PlantUML builder.
Computes layout rules, participant ordering, skinparams, arrow directions,
and hidden alignment edges to ensure deterministic, clean PlantUML output.
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
            "skinparam handwritten false",
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
        """Compute layout plan for Component Diagram."""
        total_elements = len(diagram.all_elements())
        # Select orientation based on diagram breadth vs depth
        if len(diagram.business_packages) > 2 or total_elements > 6:
            direction_directive = "left to right direction"
        else:
            direction_directive = "top to bottom direction"

        # Organize package order deterministically by package ID
        packages_sorted = sorted(diagram.business_packages, key=lambda p: p.id)
        package_order = [pkg.id for pkg in packages_sorted]

        # Gather standalone elements (not contained in any package)
        packaged_ids: Set[str] = set()
        for pkg in diagram.business_packages:
            packaged_ids.update(pkg.capability_ids)

        standalone_ids = sorted([
            elem.id for elem in diagram.all_elements()
            if elem.id not in packaged_ids
        ])

        # Formatted arrows for relationships
        formatted_arrows: Dict[Tuple[str, str], str] = {}
        connected_pairs: Set[Tuple[str, str]] = set()

        for rel in sorted(diagram.relationships, key=lambda r: (r.source_id, r.target_id)):
            pair = (rel.source_id, rel.target_id)
            connected_pairs.add(pair)
            connected_pairs.add((rel.target_id, rel.source_id))
            direction_str = rel.direction.strip()
            # If default '-->', apply smart layout direction
            if direction_str in ("-->", "->"):
                source_elem = diagram.get_element_by_id(rel.source_id)
                target_elem = diagram.get_element_by_id(rel.target_id)
                
                # Rule: Actors connect to capabilities rightward or downward
                if source_elem and source_elem.__class__.__name__ == "Actor":
                    formatted_arrows[pair] = "-right->" if direction_directive == "left to right direction" else "-down->"
                # Rule: Capabilities connect to Databases downward
                elif target_elem and target_elem.__class__.__name__ == "Database":
                    formatted_arrows[pair] = "-down->"
                else:
                    formatted_arrows[pair] = "-down->" if direction_directive == "top to bottom direction" else "-right->"
            else:
                formatted_arrows[pair] = direction_str

        # Compute hidden alignment edges between adjacent packages
        hidden_alignment_edges: List[str] = []
        if len(package_order) > 1:
            align_dir = "right" if direction_directive == "left to right direction" else "down"
            for i in range(len(package_order) - 1):
                p1, p2 = package_order[i], package_order[i + 1]
                hidden_alignment_edges.append(f"{p1} -[hidden]{align_dir}-> {p2}")

        # Compute hidden alignment edges between un-connected databases
        databases_sorted = sorted(diagram.databases, key=lambda d: d.id)
        if len(databases_sorted) > 1:
            for i in range(len(databases_sorted) - 1):
                db1, db2 = databases_sorted[i].id, databases_sorted[i + 1].id
                if (db1, db2) not in connected_pairs:
                    hidden_alignment_edges.append(f"{db1} -[hidden]right-> {db2}")

        return PlannedComponentLayout(
            direction_directive=direction_directive,
            package_order=package_order,
            standalone_element_order=standalone_ids,
            formatted_arrows=formatted_arrows,
            hidden_alignment_edges=hidden_alignment_edges,
        )

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
