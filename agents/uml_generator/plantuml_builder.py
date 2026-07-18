"""PlantUML Builder Factory and Per-Diagram Builders.

Translates canonical diagram models (with stable IDs) into syntactically valid,
deterministic PlantUML syntax using Layout Planner directives.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from schemas.canonical_diagram import (
    BaseCanonicalDiagram,
    ComponentDiagramCanonical,
    SequenceDiagramCanonical,
    BaseElement,
    Actor,
    ExternalSystem,
    BusinessCapability,
    Database,
    BusinessPackage,
    Relationship,
)
from agents.uml_generator.layout_planner import (
    LayoutPlanner,
    PlannedComponentLayout,
    PlannedSequenceLayout,
)
from config.logging import get_logger

logger = get_logger("agents.uml_generator.plantuml_builder")


# ---------------------------------------------------------------------------
# Abstract Base Builder
# ---------------------------------------------------------------------------

class BasePlantUMLBuilder(ABC):
    """Abstract interface for per-diagram PlantUML builders."""

    @abstractmethod
    def build(self, diagram: BaseCanonicalDiagram, layout: Optional[Any] = None) -> str:
        """Compile a canonical diagram into PlantUML syntax string."""
        pass


# ---------------------------------------------------------------------------
# Component Diagram Builder
# ---------------------------------------------------------------------------

class ComponentPlantUMLBuilder(BasePlantUMLBuilder):
    """Deterministic PlantUML compiler for Component Diagrams."""

    def build(self, diagram: BaseCanonicalDiagram, layout: Optional[Any] = None) -> str:
        if not isinstance(diagram, ComponentDiagramCanonical):
            # Attempt to convert or cast
            if hasattr(diagram, "business_capabilities"):
                diagram = ComponentDiagramCanonical.model_validate(diagram.model_dump())
            else:
                raise ValueError("Expected ComponentDiagramCanonical instance")

        if layout is None:
            layout = LayoutPlanner.plan_component_layout(diagram)

        lines: List[str] = ["@startuml"]

        # Title
        if diagram.metadata.title:
            lines.append(f"title {diagram.metadata.title}")

        # Orientation & Skinparams
        lines.append(layout.direction_directive)
        for param in layout.skinparams:
            lines.append(param)
        lines.append("")

        # Track elements declared in packages to prevent double declaration
        declared_ids = set()

        # 1. Render Packages & Contained Capabilities/Databases
        for pkg in diagram.business_packages:
            lines.append(f'package "{pkg.name}" {{')
            for cap_id in pkg.capability_ids:
                elem = diagram.get_element_by_id(cap_id)
                if elem:
                    lines.append(self._format_element_declaration(elem, indent="  "))
                    declared_ids.add(elem.id)
            lines.append("}")
            lines.append("")

        # 2. Render Actors
        for actor in diagram.actors:
            if actor.id not in declared_ids:
                lines.append(f'actor "{actor.name}" as {actor.id}')
                declared_ids.add(actor.id)
        if diagram.actors:
            lines.append("")

        # 3. Render External Systems
        for sys_elem in diagram.external_systems:
            if sys_elem.id not in declared_ids:
                stereo = f" <<{sys_elem.technology}>>" if sys_elem.technology else " <<External System>>"
                lines.append(f'component "{sys_elem.name}" as {sys_elem.id}{stereo}')
                declared_ids.add(sys_elem.id)
        if diagram.external_systems:
            lines.append("")

        # 4. Render Standalone Capabilities
        for cap in diagram.business_capabilities:
            if cap.id not in declared_ids:
                lines.append(self._format_element_declaration(cap))
                declared_ids.add(cap.id)

        # 5. Render Standalone Databases
        for db in diagram.databases:
            if db.id not in declared_ids:
                lines.append(self._format_element_declaration(db))
                declared_ids.add(db.id)
        lines.append("")

        # 6. Render Relationships
        for rel in diagram.relationships:
            pair = (rel.source_id, rel.target_id)
            arrow = layout.formatted_arrows.get(pair, rel.direction or "-->")
            label_str = f" : {rel.label}" if rel.label else ""
            lines.append(f"{rel.source_id} {arrow} {rel.target_id}{label_str}")

        lines.append("@enduml")
        return "\n".join(lines)

    @staticmethod
    def _format_element_declaration(elem: BaseElement, indent: str = "") -> str:
        """Format PlantUML declaration string for an architectural element."""
        if isinstance(elem, Actor):
            return f'{indent}actor "{elem.name}" as {elem.id}'
        elif isinstance(elem, Database):
            stereo = f" <<{elem.db_type}>>" if elem.db_type else ""
            return f'{indent}database "{elem.name}" as {elem.id}{stereo}'
        elif isinstance(elem, BusinessCapability):
            stereo = f" <<{elem.stereotype}>>" if elem.stereotype else ""
            return f'{indent}component "{elem.name}" as {elem.id}{stereo}'
        elif isinstance(elem, ExternalSystem):
            stereo = f" <<{elem.technology}>>" if elem.technology else " <<External System>>"
            return f'{indent}component "{elem.name}" as {elem.id}{stereo}'
        else:
            return f'{indent}component "{elem.name}" as {elem.id}'


# ---------------------------------------------------------------------------
# Sequence Diagram Builder
# ---------------------------------------------------------------------------

class SequencePlantUMLBuilder(BasePlantUMLBuilder):
    """Deterministic PlantUML compiler for Sequence Diagrams."""

    def build(self, diagram: BaseCanonicalDiagram, layout: Optional[Any] = None) -> str:
        if not isinstance(diagram, SequenceDiagramCanonical):
            if hasattr(diagram, "participants"):
                diagram = SequenceDiagramCanonical.model_validate(diagram.model_dump())
            else:
                raise ValueError("Expected SequenceDiagramCanonical instance")

        if layout is None:
            layout = LayoutPlanner.plan_sequence_layout(diagram)

        lines: List[str] = ["@startuml"]

        # Title
        if diagram.metadata.title:
            lines.append(f"title {diagram.metadata.title}")

        # Autonumber & Skinparams
        if layout.autonumber:
            lines.append("autonumber")
        for param in layout.skinparams:
            lines.append(param)
        lines.append("")

        # 1. Render Participant Declarations in explicit left-to-right order
        for p_id in layout.participant_order:
            elem = diagram.get_element_by_id(p_id)
            if elem:
                lines.append(self._format_participant_declaration(elem))
        lines.append("")

        # 2. Render Sequence Interactions in step order
        for rel in layout.ordered_relationships:
            arrow = rel.direction if rel.direction in ("->", "-->", "->>", "-->>", "<-", "<--") else "->"
            label_str = rel.label or "Call"
            if rel.protocol:
                label_str = f"[{rel.protocol}] {label_str}"
            lines.append(f"{rel.source_id} {arrow} {rel.target_id} : {label_str}")

        lines.append("@enduml")
        return "\n".join(lines)

    @staticmethod
    def _format_participant_declaration(elem: BaseElement) -> str:
        """Format participant lifeline declaration."""
        if isinstance(elem, Actor):
            return f'actor "{elem.name}" as {elem.id}'
        elif isinstance(elem, Database):
            return f'database "{elem.name}" as {elem.id}'
        elif isinstance(elem, ExternalSystem):
            return f'participant "{elem.name}" as {elem.id}'
        else:
            return f'participant "{elem.name}" as {elem.id}'


# ---------------------------------------------------------------------------
# PlantUML Builder Factory
# ---------------------------------------------------------------------------

class PlantUMLBuilderFactory:
    """Factory for resolving per-diagram PlantUML builders."""

    _builders: Dict[str, BasePlantUMLBuilder] = {
        "component": ComponentPlantUMLBuilder(),
        "sequence": SequencePlantUMLBuilder(),
    }

    @classmethod
    def get_builder(cls, diagram_type: str) -> BasePlantUMLBuilder:
        """Get per-diagram builder instance by diagram type.
        
        Args:
            diagram_type: Diagram type ('component' or 'sequence').
            
        Returns:
            Concrete BasePlantUMLBuilder implementation.
        """
        normalized = diagram_type.lower()
        if normalized in cls._builders:
            return cls._builders[normalized]
        else:
            logger.warning("Unsupported diagram_type '%s' for builder, defaulting to Component builder", diagram_type)
            return cls._builders["component"]

    @classmethod
    def register_builder(cls, diagram_type: str, builder: BasePlantUMLBuilder) -> None:
        """Register a new per-diagram builder."""
        cls._builders[diagram_type.lower()] = builder
