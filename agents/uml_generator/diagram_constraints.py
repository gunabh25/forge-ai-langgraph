"""Per-diagram-type constraint definitions for UML generation.

This module is the **single source of truth** for diagram-specific constraints.
To add or modify constraints for a diagram type, update ``DIAGRAM_CONSTRAINTS``
— no other files need to change.

Constraints are plain ``str → str | int | bool`` mappings that are rendered
into a human-readable block and injected into the LLM prompt by
``PromptBuilder``.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Constraint registry
# ---------------------------------------------------------------------------

DIAGRAM_CONSTRAINTS: dict[str, dict[str, str | int | bool]] = {
    "component": {
        "abstraction": "high",
        "max_components": 8,
        "implementation_details": False,
    },
    "sequence": {
        "max_participants": 10,
        "max_messages": 20,
        "business_flow_only": True,
    },
    "activity": {
        "max_swimlanes": 5,
        "max_steps": 15,
        "business_flow_only": True,
    },
    "deployment": {
        "abstraction": "infrastructure",
        "max_nodes": 10,
        "show_protocols": True,
    },
    "class": {
        "abstraction": "domain",
        "max_classes": 12,
        "implementation_details": False,
    },
    "use case": {
        "max_actors": 6,
        "max_use_cases": 12,
        "implementation_details": False,
    },
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_constraints(diagram_type: str) -> dict[str, str | int | bool]:
    """Return constraints for *diagram_type* (case-insensitive).

    Returns an empty dict for unknown types so callers never need to
    guard against ``None``.
    """
    return DIAGRAM_CONSTRAINTS.get(diagram_type.lower(), {})


def format_constraints_block(constraints: dict[str, str | int | bool]) -> str:
    """Render a constraints dict as a readable prompt block.

    Returns an empty string when *constraints* is empty, so it can be
    unconditionally concatenated into a prompt without introducing blank
    sections.

    Example output::

        ## Diagram Constraints
        - abstraction: high
        - max_components: 8
        - implementation_details: false
    """
    if not constraints:
        return ""

    lines = ["## Diagram Constraints"]
    for key, value in constraints.items():
        # Normalize booleans to lowercase strings for prompt clarity.
        if isinstance(value, bool):
            display_value = "true" if value else "false"
        else:
            display_value = str(value)

        label = key.replace("_", " ")
        lines.append(f"- {label}: {display_value}")

    lines.append("")  # trailing newline for clean concatenation
    return "\n".join(lines)
