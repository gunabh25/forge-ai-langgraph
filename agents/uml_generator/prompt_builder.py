"""Prompt construction for UML diagram generation.

This module is intentionally decoupled from LangGraph, ForgeState, and LLM
invocation.  Its single responsibility is assembling the final prompt string
from a diagram type, an architecture summary, and a set of templates.

Templates are loaded from Markdown files in the ``prompts/`` directory next to
this module.  If no file exists for a given diagram type, a built-in inline
fallback is used.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from agents.uml_generator.diagram_constraints import (
    format_constraints_block,
    get_constraints,
)


# ---------------------------------------------------------------------------
# Type alias for template functions
# ---------------------------------------------------------------------------
TemplateFunction = Callable[[str], str]
"""A template function receives the architecture summary and returns
the fully-rendered prompt body for a specific diagram type."""


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).parent / "prompts"


# ---------------------------------------------------------------------------
# File-based template loader
# ---------------------------------------------------------------------------

def _load_template_from_file(diagram_type: str, architecture_summary: str) -> str | None:
    """Try to load a ``.md`` template for *diagram_type* from the prompts dir.

    Returns the rendered template string with ``{architecture_summary}``
    replaced, or ``None`` if no file exists for the given type.
    """
    filename = diagram_type.lower().replace(" ", "_") + ".md"
    filepath = _PROMPTS_DIR / filename
    if not filepath.is_file():
        return None
    raw = filepath.read_text(encoding="utf-8")
    return raw.replace("{architecture_summary}", architecture_summary)


# ---------------------------------------------------------------------------
# Built-in inline fallback templates
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
# Default inline-template registry (used as fallback)
# ---------------------------------------------------------------------------

_INLINE_TEMPLATES: dict[str, TemplateFunction] = {
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

    **Template resolution order** (per diagram type):

    1. Markdown file in ``prompts/<type>.md``  — production-grade templates.
    2. Runtime-registered callable via ``register_template()``.
    3. Built-in inline fallback (``_INLINE_TEMPLATES``).
    4. Generic catch-all for completely unknown types.

    New diagram types can be supported by simply dropping a ``.md`` file into
    the ``prompts/`` directory — no code changes required.

    Usage::

        builder = PromptBuilder()
        system, user = builder.build_prompt("component", summary_text)
    """

    def __init__(self) -> None:
        # Runtime overrides / additions. Starts empty — inline defaults are
        # consulted directly from the module-level dict as a fallback.
        self._custom_templates: dict[str, TemplateFunction] = {}

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
        self._custom_templates[diagram_type.lower()] = template_fn

    def build_prompt(
        self,
        diagram_type: str,
        architecture_summary: str,
        constraints: dict[str, str | int | bool] | None = None,
    ) -> tuple[str, str]:
        """Build the system and user prompt for the given diagram type.

        Args:
            diagram_type: The kind of UML diagram to generate
                          (e.g. ``"component"``, ``"sequence"``).
            architecture_summary: A pre-built textual summary of the
                                  architecture (produced by ``ContextBuilder``).
            constraints: Optional per-diagram constraints.  When ``None``
                         (the default), constraints are auto-resolved from
                         ``diagram_constraints.DIAGRAM_CONSTRAINTS``.
                         Pass an explicit dict to override, or ``{}`` to
                         suppress constraints entirely.

        Returns:
            A ``(system_prompt, user_prompt)`` tuple ready to be passed to
            an LLM.  The system prompt contains shared generation rules; the
            user prompt contains diagram-specific instructions plus the
            architecture summary.
        """
        key = diagram_type.lower()

        # -- resolve constraints -----------------------------------------------
        if constraints is None:
            constraints = get_constraints(key)
        constraints_block = format_constraints_block(constraints)

        # 1. Try file-based template first (highest priority).
        user_prompt = _load_template_from_file(key, architecture_summary)

        # 2. Try runtime-registered custom template.
        if user_prompt is None:
            custom_fn = self._custom_templates.get(key)
            if custom_fn is not None:
                user_prompt = custom_fn(architecture_summary)

        # 3. Try built-in inline template.
        if user_prompt is None:
            inline_fn = _INLINE_TEMPLATES.get(key)
            if inline_fn is not None:
                user_prompt = inline_fn(architecture_summary)

        # 4. Generic catch-all for completely unknown types.
        if user_prompt is None:
            user_prompt = (
                f"Generate a PlantUML **{diagram_type}** diagram based on the "
                f"architecture summary below.\n\n"
                f"Architecture Summary:\n{architecture_summary}"
            )

        # -- inject constraints into the user prompt ---------------------------
        if constraints_block:
            user_prompt = f"{user_prompt}\n\n{constraints_block}"

        system_prompt = (
            f"You are a specialized UML Generator Agent.\n"
            f"Your task is to generate valid PlantUML syntax for a "
            f"{diagram_type} diagram.\n\n"
            f"{_SYSTEM_RULES}"
        )

        return system_prompt, user_prompt

    @property
    def supported_diagram_types(self) -> list[str]:
        """Return the currently registered diagram type keys.

        Includes types available from files, custom registrations, and
        inline defaults.
        """
        file_types: set[str] = set()
        if _PROMPTS_DIR.is_dir():
            for f in _PROMPTS_DIR.iterdir():
                if f.suffix == ".md":
                    file_types.add(f.stem.replace("_", " "))

        return sorted(
            file_types | set(self._custom_templates.keys()) | set(_INLINE_TEMPLATES.keys())
        )
