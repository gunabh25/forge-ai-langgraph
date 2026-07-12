"""Prompt construction for UML diagram generation.

This module is intentionally decoupled from LangGraph, ForgeState, and LLM
invocation.  Its single responsibility is assembling the final prompt string
from a diagram type, an architecture summary, an optional diagram plan, and
a set of per-type profiles / constraints.

Template resolution order (per diagram type)
--------------------------------------------
1. Markdown file in ``prompts/<type>.md``  — highest-priority overrides.
2. Runtime-registered callable via ``register_template()``.
3. Profile-driven inline template from ``diagram_profile.DIAGRAM_PROFILES``.
4. Generic catch-all for completely unknown types.

Markdown files in ``prompts/`` are intentionally left as-is when they exist —
they represent manually curated, production-quality prompts.

New diagram types can be supported by either:
- Dropping a ``.md`` file into ``prompts/``, or
- Adding an entry to ``diagram_profile.DIAGRAM_PROFILES``.
No code changes are required in either case.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.settings import settings
from agents.uml_generator.diagram_constraints import (
    format_constraints_block,
    get_constraints,
)
from agents.uml_generator.diagram_profile import DiagramProfile, get_profile


# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

TemplateFunction = Callable[[str], str]
"""A template function receives the architecture summary and returns the
fully-rendered prompt body for a specific diagram type."""


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).parent / "prompts"


# ---------------------------------------------------------------------------
# File-based template loader (highest priority)
# ---------------------------------------------------------------------------


def _load_template_from_file(diagram_type: str, context: str, few_shot: str) -> str | None:
    """Try to load a ``.md`` template for *diagram_type* from the prompts dir.

    Returns the rendered template string with ``{context_block}``
    and ``{few_shot}`` replaced, or ``None`` if no file exists.
    """
    filename = diagram_type.lower().replace(" ", "_") + ".md"
    filepath = _PROMPTS_DIR / filename
    if not filepath.is_file():
        return None
    raw = filepath.read_text(encoding="utf-8")
    return raw.replace("{context_block}", context).replace("{few_shot}", few_shot)


# ---------------------------------------------------------------------------
# Profile-driven inline template renderer
# ---------------------------------------------------------------------------


def _render_profile_template(
    profile: DiagramProfile,
    diagram_type: str,
    architecture_summary: str,
) -> str:
    """Render a structured, architect-grade prompt from a ``DiagramProfile``.

    The output follows a fixed schema that explicitly tells the LLM:
    - who the audience is
    - what abstraction level to maintain
    - what the diagram's objective is
    - what to include
    - what to avoid
    - hard constraints (if any)
    """
    include_items = "\n".join(f"  - {item}" for item in profile.include)
    avoid_items = "\n".join(f"  - {item}" for item in profile.avoid)

    sections = [
        f"Generate a PlantUML **{diagram_type.title()} Diagram**.\n",
        f"**Audience**: {profile.audience}",
        f"**Abstraction**: {profile.abstraction}",
        f"**Objective**: {profile.objective}",
        f"**Include**:\n{include_items}",
        f"**Avoid**:\n{avoid_items}",
    ]

    if profile.max_note:
        sections.append(f"**Hard constraint**: {profile.max_note}")

    sections.append(f"\n## Architecture Summary\n\n{architecture_summary}")

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Shared system prompt rules
# ---------------------------------------------------------------------------

_SYSTEM_RULES = (
    "CRITICAL RULES:\n"
    "1. Generate EXACTLY ONE PlantUML diagram. Never combine multiple diagrams.\n"
    "2. You must ONLY generate valid PlantUML code. Do NOT render images.\n"
    "3. Respond ONLY with the raw PlantUML syntax string. "
    "The string must start with @startuml and end with @enduml.\n"
    "4. DO NOT include markdown formatting blocks "
    "(like ```plantuml or ```puml). Just output the raw syntax.\n"
    "5. Use ONLY components, participants, and relationships that are "
    "explicitly present in the Architecture Summary or Diagram Plan. "
    "Do NOT invent services, gateways, or infrastructure not mentioned there.\n"
    "6. Do NOT include commentary, explanations, or notes outside the PlantUML block.\n"
    "7. **Audience**: Architecture Review Board. Think like a Principal Software Architect.\n"
    "8. **Priority**: Emphasize Business Capabilities over Implementation details.\n"
    "9. **Avoid**: Implementation classes, Frameworks, Infrastructure, Controllers, "
    "Repositories, Middleware, Internal orchestration, Helper modules."
)

_FEW_SHOT_COMPONENT = """
## Few-Shot Example

**GOOD example:**
Requirement: Online Food Delivery
Component Diagram:
- Customer
- Restaurant
- Order Service
- Payment Service
- Delivery Service

**BAD example (Implementation Leakage):**
- OrderRepository
- JWT Middleware
- Logger
- Redis Cache
- Auth Controller
"""

_FEW_SHOT_SEQUENCE = """
## Few-Shot Example

**GOOD example:**
- Customer -> Order Service: Place Order
- Order Service -> Payment Service: Process Payment
- Payment Service --> Order Service: Payment Confirmed
- Order Service -> Restaurant: Send Order

**BAD example (Implementation Leakage):**
- Auth Controller -> JWT Middleware: Validate Token
- JWT Middleware -> Redis Cache: Check Session
- Order Service -> OrderRepository: save(order)
- OrderRepository -> Logger: log("saved")
"""


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------


class PromptBuilder:
    """Builds the final LLM prompt from a diagram type, architecture summary,
    optional diagram plan, and optional constraints.

    **Template resolution order** (per diagram type):

    1. Markdown file in ``prompts/<type>.md``  — production-grade templates.
    2. Runtime-registered callable via ``register_template()``.
    3. Profile-driven inline template from ``DIAGRAM_PROFILES``.
    4. Generic catch-all for completely unknown types.

    Usage::

        builder = PromptBuilder()
        system, user = builder.build_prompt(
            diagram_type="component",
            architecture_summary=summary_text,
            diagram_plan=plan_text,     # optional — injected from planning step
        )
    """

    def __init__(self) -> None:
        # Runtime overrides / additions.
        self._custom_templates: dict[str, TemplateFunction] = {}

    # -- public API ---------------------------------------------------------

    def register_template(self, diagram_type: str, template_fn: TemplateFunction) -> None:
        """Register (or override) a template for *diagram_type*.

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
        diagram_plan: str | None = None,
        constraints: dict[str, str | int | bool] | None = None,
    ) -> tuple[str, str]:
        """Build the system and user prompt for the given diagram type.

        Args:
            diagram_type: The kind of UML diagram to generate
                          (e.g. ``"component"``, ``"sequence"``).
            architecture_summary: A pre-built Business Architecture Summary
                                  produced by ``ContextBuilder``.
            diagram_plan: Optional output of the planning step. When provided,
                          it is appended as a ``## Diagram Plan`` section that
                          scopes the LLM's generation strictly to planned
                          elements.
            constraints: Optional per-diagram constraints.  When ``None``
                         (the default), constraints are auto-resolved from
                         ``diagram_constraints.DIAGRAM_CONSTRAINTS``.
                         Pass ``{}`` to suppress constraints entirely.

        Returns:
            A ``(system_prompt, user_prompt)`` tuple ready to be passed to
            an LLM.
        """
        key = diagram_type.lower()

        # -- resolve constraints -----------------------------------------------
        if constraints is None:
            constraints = get_constraints(key)
        constraints_block = format_constraints_block(constraints)

        # -- resolve context block ---------------------------------------------
        # Prefer the diagram_plan if available (Task 5 requirement)
        if diagram_plan and diagram_plan.strip():
            context_block = f"## Diagram Plan\n\n{diagram_plan.strip()}"
        else:
            context_block = f"## Architecture Summary\n\n{architecture_summary.strip()}"

        # -- resolve few shot --------------------------------------------------
        few_shot = ""
        if settings.ENABLE_FEW_SHOT:
            if key == "component":
                few_shot = _FEW_SHOT_COMPONENT
            elif key == "sequence":
                few_shot = _FEW_SHOT_SEQUENCE

        # -- resolve user prompt -----------------------------------------------

        # 1. Try file-based template first (highest priority).
        user_prompt = _load_template_from_file(key, context_block, few_shot)

        # 2. Try runtime-registered custom template.
        if user_prompt is None:
            custom_fn = self._custom_templates.get(key)
            if custom_fn is not None:
                user_prompt = custom_fn(architecture_summary)

        # 3. Try profile-driven inline template.
        if user_prompt is None:
            profile = get_profile(key)
            if profile is not None:
                user_prompt = _render_profile_template(
                    profile, diagram_type, architecture_summary
                )

        # 4. Generic catch-all for completely unknown types.
        if user_prompt is None:
            user_prompt = (
                f"Generate a PlantUML **{diagram_type}** diagram based on the "
                f"context below.\n\n"
                f"Use ONLY elements explicitly present in the context.\n\n"
                f"{context_block}\n\n"
                f"{few_shot}"
            )

        # -- inject constraints ------------------------------------------------
        if constraints_block:
            user_prompt = f"{user_prompt}\n\n{constraints_block}"

        # -- system prompt -----------------------------------------------------
        system_prompt = (
            f"You are a specialized UML Generator Agent acting as a Senior "
            f"Software Architect.\n"
            f"Your task is to generate valid PlantUML syntax for a "
            f"{diagram_type} diagram that would pass a rigorous architecture "
            f"review.\n\n"
            f"{_SYSTEM_RULES}"
        )

        return system_prompt, user_prompt

    @property
    def supported_diagram_types(self) -> list[str]:
        """Return the currently registered diagram type keys."""
        from agents.uml_generator.diagram_profile import DIAGRAM_PROFILES

        file_types: set[str] = set()
        if _PROMPTS_DIR.is_dir():
            for f in _PROMPTS_DIR.iterdir():
                if f.suffix == ".md":
                    file_types.add(f.stem.replace("_", " "))

        return sorted(
            file_types
            | set(self._custom_templates.keys())
            | set(DIAGRAM_PROFILES.keys())
        )
