"""Prompt construction for UML diagram generation.

This module is intentionally decoupled from LangGraph, ForgeState, and LLM
invocation.  Its single responsibility is assembling the final prompt string
from a diagram type, an architecture summary, and a set of templates.
"""

from __future__ import annotations

from typing import Callable


# ---------------------------------------------------------------------------
# Type alias for template functions
# ---------------------------------------------------------------------------
TemplateFunction = Callable[[str], str]
"""A template function receives the architecture summary and returns
the fully-rendered prompt body for a specific diagram type."""


# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------

def _component_template(architecture_summary: str) -> str:
    return (
        "Generate a PlantUML **Component Diagram** that shows the major system "
        "components, their interfaces, and dependencies.\n\n"
        "Guidelines:\n"
        "- Represent each service or module as a component.\n"
        "- Use `[ComponentName]` notation.\n"
        "- Show dependencies with `-->` arrows.\n"
        "- Group related components inside packages where appropriate.\n\n"
        f"Architecture Summary:\n{architecture_summary}"
    )


def _sequence_template(architecture_summary: str) -> str:
    return (
        "Generate a PlantUML **Sequence Diagram** that illustrates the primary "
        "interactions between actors and system components.\n\n"
        "Guidelines:\n"
        "- Include all primary actors and the services they interact with.\n"
        "- Model the main success scenario (happy path).\n"
        "- Use `participant`, `actor`, and `->` message arrows.\n"
        "- Keep the number of messages focused on the core flow.\n\n"
        f"Architecture Summary:\n{architecture_summary}"
    )


def _activity_template(architecture_summary: str) -> str:
    return (
        "Generate a PlantUML **Activity Diagram** that captures the main "
        "business workflow from trigger to completion.\n\n"
        "Guidelines:\n"
        "- Start with `start` and end with `stop`.\n"
        "- Use decision diamonds (`:condition;`) for branching logic.\n"
        "- Use swim-lanes (`|LaneName|`) if multiple actors are involved.\n"
        "- Focus on high-level business steps, not implementation details.\n\n"
        f"Architecture Summary:\n{architecture_summary}"
    )


def _deployment_template(architecture_summary: str) -> str:
    return (
        "Generate a PlantUML **Deployment Diagram** that shows the physical "
        "or cloud infrastructure and how artifacts are deployed.\n\n"
        "Guidelines:\n"
        "- Use `node`, `database`, and `cloud` stereotypes.\n"
        "- Map services to their deployment targets.\n"
        "- Show network boundaries and communication protocols.\n\n"
        f"Architecture Summary:\n{architecture_summary}"
    )


def _class_template(architecture_summary: str) -> str:
    return (
        "Generate a PlantUML **Class Diagram** that models the key domain "
        "entities and their relationships.\n\n"
        "Guidelines:\n"
        "- Focus on high-level domain objects, not utility classes.\n"
        "- Show associations, inheritance, and composition.\n"
        "- Include key attributes and methods only where they clarify design.\n\n"
        f"Architecture Summary:\n{architecture_summary}"
    )


def _use_case_template(architecture_summary: str) -> str:
    return (
        "Generate a PlantUML **Use Case Diagram** that captures the primary "
        "actors and the use cases they participate in.\n\n"
        "Guidelines:\n"
        "- Use `actor` for each primary actor.\n"
        "- Use `usecase` for each high-level capability.\n"
        "- Draw associations between actors and their use cases.\n"
        "- Group use cases inside a `rectangle` representing the system boundary.\n\n"
        f"Architecture Summary:\n{architecture_summary}"
    )


# ---------------------------------------------------------------------------
# Default template registry
# ---------------------------------------------------------------------------

_DEFAULT_TEMPLATES: dict[str, TemplateFunction] = {
    "component": _component_template,
    "sequence": _sequence_template,
    "activity": _activity_template,
    "deployment": _deployment_template,
    "class": _class_template,
    "use case": _use_case_template,
}


# ---------------------------------------------------------------------------
# System prompt (shared across all diagram types)
# ---------------------------------------------------------------------------

_SYSTEM_RULES = (
    "CRITICAL RULES:\n"
    "1. Generate EXACTLY ONE PlantUML diagram. Never combine multiple diagrams.\n"
    "2. You must ONLY generate valid PlantUML code. Do NOT render images.\n"
    "3. Respond ONLY with the raw PlantUML syntax string. "
    "The string must start with @startuml and end with @enduml.\n"
    "4. DO NOT include markdown formatting blocks "
    "(like ```plantuml or ```puml). Just output the raw syntax."
)


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------

class PromptBuilder:
    """Builds the final LLM prompt from a diagram type and an architecture summary.

    New diagram types can be registered at runtime via ``register_template``
    without modifying any existing code.

    Usage::

        builder = PromptBuilder()
        system, user = builder.build_prompt("component", summary_text)
    """

    def __init__(self) -> None:
        # Copy defaults so mutations don't leak across instances.
        self._templates: dict[str, TemplateFunction] = dict(_DEFAULT_TEMPLATES)

    # -- public API ---------------------------------------------------------

    def register_template(self, diagram_type: str, template_fn: TemplateFunction) -> None:
        """Register (or override) a template for *diagram_type*.

        This is the extension point: callers can add support for new diagram
        types without touching existing logic.

        Args:
            diagram_type: A case-insensitive diagram type key (e.g. ``"erd"``).
            template_fn:  A callable ``(architecture_summary: str) -> str``
                          that returns the user-facing prompt body.
        """
        self._templates[diagram_type.lower()] = template_fn

    def build_prompt(self, diagram_type: str, architecture_summary: str) -> tuple[str, str]:
        """Build the system and user prompt for the given diagram type.

        Args:
            diagram_type: The kind of UML diagram to generate
                          (e.g. ``"component"``, ``"sequence"``).
            architecture_summary: A pre-built textual summary of the
                                  architecture (produced by ``ContextBuilder``).

        Returns:
            A ``(system_prompt, user_prompt)`` tuple ready to be passed to
            an LLM.  The system prompt contains shared generation rules; the
            user prompt contains diagram-specific instructions plus the
            architecture summary.
        """
        key = diagram_type.lower()
        template_fn = self._templates.get(key)

        if template_fn is not None:
            user_prompt = template_fn(architecture_summary)
        else:
            # Graceful fallback for unregistered types – still produces a
            # usable prompt rather than raising.
            user_prompt = (
                f"Generate a PlantUML **{diagram_type}** diagram based on the "
                f"architecture summary below.\n\n"
                f"Architecture Summary:\n{architecture_summary}"
            )

        system_prompt = (
            f"You are a specialized UML Generator Agent.\n"
            f"Your task is to generate valid PlantUML syntax for a "
            f"{diagram_type} diagram.\n\n"
            f"{_SYSTEM_RULES}"
        )

        return system_prompt, user_prompt

    @property
    def supported_diagram_types(self) -> list[str]:
        """Return the currently registered diagram type keys."""
        return list(self._templates.keys())
