"""Canonical Diagram Validator.

Validates raw JSON structure, Pydantic schema compliance, ID reference integrity,
and architectural traceability for canonical diagram representations before layout planning.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import ValidationError

from schemas.canonical_diagram import (
    BaseCanonicalDiagram,
    ComponentDiagramCanonical,
    SequenceDiagramCanonical,
)
from core.business_normalizer import normalize_name
from config.logging import get_logger

logger = get_logger("agents.uml_generator.canonical_validator")


from agents.uml_generator.canonical_parser import CanonicalDiagramParser, CanonicalParseError


class CanonicalValidationError(Exception):
    """Exception raised when canonical diagram validation fails."""
    pass


class CanonicalDiagramValidator:
    """Validator for canonical diagram models."""

    @staticmethod
    def parse_and_validate_schema(
        raw_input: Union[str, Dict[str, Any]],
        diagram_type: str
    ) -> BaseCanonicalDiagram:
        """Parse raw JSON input and validate against the specific canonical diagram schema.
        
        Args:
            raw_input: Raw JSON string or dictionary model.
            diagram_type: Diagram type ('component' or 'sequence').
            
        Returns:
            Validated BaseCanonicalDiagram subclass (ComponentDiagramCanonical or SequenceDiagramCanonical).
        """
        try:
            data = CanonicalDiagramParser.parse(raw_input)
        except CanonicalParseError as e:
            raise CanonicalValidationError(str(e)) from e

        normalized_type = diagram_type.lower()
        try:
            if normalized_type == "component":
                return ComponentDiagramCanonical.model_validate(data)
            elif normalized_type == "sequence":
                return SequenceDiagramCanonical.model_validate(data)
            else:
                # Fallback to Component diagram model for generic types
                logger.warning("Unknown diagram_type '%s', falling back to Component model", diagram_type)
                return ComponentDiagramCanonical.model_validate(data)
        except ValidationError as val_err:
            raise CanonicalValidationError(f"Canonical schema validation error for {diagram_type}: {val_err}")

    @staticmethod
    def validate_references(diagram: BaseCanonicalDiagram) -> None:
        """Verify internal reference integrity (stable ID references).
        
        Checks that:
        - Source and target IDs in relationships exist in the diagram.
        - Package capability IDs exist in the diagram.
        - Sequence participant IDs exist in the diagram.
        """
        defined_ids = diagram.all_element_ids()
        missing_refs: List[str] = []

        # Check relationships
        for rel in diagram.relationships:
            if rel.source_id not in defined_ids:
                missing_refs.append(f"Relationship source_id '{rel.source_id}' not found in defined elements")
            if rel.target_id not in defined_ids:
                missing_refs.append(f"Relationship target_id '{rel.target_id}' not found in defined elements")

        # Check Component diagram package references
        if isinstance(diagram, ComponentDiagramCanonical):
            for pkg in diagram.business_packages:
                for cap_id in pkg.capability_ids:
                    if cap_id not in defined_ids:
                        missing_refs.append(f"Package '{pkg.name}' references non-existent capability ID '{cap_id}'")

        # Check Sequence diagram participant references
        if isinstance(diagram, SequenceDiagramCanonical):
            for part_id in diagram.participants:
                if part_id not in defined_ids:
                    missing_refs.append(f"Sequence participant list contains non-existent element ID '{part_id}'")

        if missing_refs:
            error_msg = "; ".join(missing_refs)
            logger.error("Reference validation failed: %s", error_msg)
            raise CanonicalValidationError(f"Stable ID reference error: {error_msg}")

    @staticmethod
    def validate_traceability(
        diagram: BaseCanonicalDiagram,
        allowed_normalized_names: Set[str]
    ) -> List[str]:
        """Check for invented business capabilities not present in approved architecture.
        
        Args:
            diagram: The canonical diagram instance.
            allowed_normalized_names: Set of normalized allowed capability names from plan/architecture.
            
        Returns:
            List of hallucinated/unapproved capability display names.
        """
        if not allowed_normalized_names:
            return []

        hallucinated: List[str] = []
        if isinstance(diagram, ComponentDiagramCanonical):
            capabilities = diagram.business_capabilities
        elif isinstance(diagram, SequenceDiagramCanonical):
            capabilities = diagram.business_capabilities
        else:
            capabilities = getattr(diagram, "business_capabilities", [])

        for cap in capabilities:
            norm = normalize_name(cap.name)
            # Check exact or substring match
            is_allowed = norm in allowed_normalized_names or any(
                norm in allowed or allowed in norm for allowed in allowed_normalized_names
            )
            if not is_allowed:
                hallucinated.append(cap.name)

        if hallucinated:
            logger.warning("Traceability warning: Found unapproved capabilities %s", hallucinated)
        return hallucinated

    @classmethod
    def validate(
        cls,
        raw_input: Union[str, Dict[str, Any]],
        diagram_type: str,
        allowed_normalized_names: Optional[Set[str]] = None,
    ) -> BaseCanonicalDiagram:
        """Full validation pipeline: Schema parsing, stable ID reference check, and traceability check."""
        diagram = cls.parse_and_validate_schema(raw_input, diagram_type)
        cls.validate_references(diagram)
        if allowed_normalized_names:
            hallucinated = cls.validate_traceability(diagram, allowed_normalized_names)
            if hallucinated:
                raise CanonicalValidationError(
                    f"Traceability violation: LLM generated unapproved business capabilities: {hallucinated}"
                )
        return diagram
