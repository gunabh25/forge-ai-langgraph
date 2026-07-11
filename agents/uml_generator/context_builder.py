"""Business Architecture Summary builder for UML generation.

This module extracts ONLY architecturally significant, business-level concepts
from the architecture JSON. It is deliberately narrow in scope:

- It NEVER invents components.
- It NEVER adds API Gateway, Auth Service, Notification Service, Audit Service,
  or any other infrastructure unless it is explicitly present in the source JSON.
- It NEVER exposes repositories, helper classes, utility modules, or parser
  internals.
- It ONLY maps a fixed set of allowlisted JSON keys to well-labeled summary
  sections.

The output is the sole input the LLM receives about the architecture. Keeping
it clean and business-focused is the primary lever for preventing hallucination
and implementation leakage in generated diagrams.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Exclusion keywords — names that match any of these are silently dropped.
# ---------------------------------------------------------------------------

_EXCLUDED_KEYWORDS: frozenset[str] = frozenset(
    {
        "helper",
        "repository",
        "repo",
        "util",
        "utility",
        "parser",
        "impl",
        "implementation",
        "internal",
        "middleware",
        "interceptor",
        "serializer",
        "deserializer",
        "factory",
        "mapper",
        "dto",
        "dao",
        "decorator",
        "mixin",
        "base",
        "abstract",
        "cache",
        "logger",
        "config",
        "settings",
        "bootstrap",
        "initializer",
        "handler",       # overly generic — usually implementation detail
        "processor",     # same
        "manager",       # same
        "provider",      # same
    }
)

# Hallucination guard: names that an LLM tends to inject but are rarely
# explicitly specified by users. Dropped unless they appear verbatim in the
# source JSON.
_HALLUCINATION_GUARD: frozenset[str] = frozenset(
    {
        "api gateway",
        "auth service",
        "authentication service",
        "authorization service",
        "notification service",
        "audit service",
        "audit log",
        "logging service",
        "monitoring service",
        "metrics service",
        "tracing service",
    }
)


# ---------------------------------------------------------------------------
# ContextBuilder
# ---------------------------------------------------------------------------


class ContextBuilder:
    """Builds a Business Architecture Summary from an architecture JSON dict.

    The summary is a compact, markdown-formatted document containing only
    architecturally significant business concepts. It is passed verbatim to
    the LLM as the sole source of architectural truth — so accuracy and
    brevity are both critical.

    Usage::

        builder = ContextBuilder()
        summary = builder.build_summary(architecture_json)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_summary(self, architecture_json: dict) -> str:
        """Build a Business Architecture Summary from *architecture_json*.

        Sections are extracted in a fixed order using an allowlisted set of
        JSON keys. Keys not in the allowlist are silently ignored — this is
        the primary mechanism preventing implementation details from leaking
        into the summary.

        Args:
            architecture_json: The architecture definition produced by the
                Solution Architect agent.

        Returns:
            A markdown-formatted Business Architecture Summary string. Returns
            a placeholder message when the dict is empty or None.
        """
        if not architecture_json:
            return "No architecture details provided."

        parts: list[str] = []

        # 1. Business Objective ------------------------------------------------
        objective = self._first_value(
            architecture_json,
            "business_objective",
            "objective",
            "system_overview",
            "overview",
        )
        if objective:
            parts.append(f"## Business Objective\n{objective}\n")

        # 2. Primary Actors ----------------------------------------------------
        actors = self._first_list(architecture_json, "primary_actors", "actors")
        actors_section = self._render_list("Primary Actors", actors)
        if actors_section:
            parts.append(actors_section)

        # 3. External Systems --------------------------------------------------
        external_systems = self._first_list(
            architecture_json, "external_systems"
        )
        ext_section = self._render_list("External Systems", external_systems)
        if ext_section:
            parts.append(ext_section)

        # 4. Major Business Capabilities ---------------------------------------
        capabilities = self._first_list(
            architecture_json,
            "major_business_services",
            "services",
            "capabilities",
        )
        cap_section = self._render_list("Major Business Capabilities", capabilities)
        if cap_section:
            parts.append(cap_section)

        # 5. Major Data Stores -------------------------------------------------
        data_stores = self._first_list(
            architecture_json, "major_databases", "databases", "data_stores"
        )
        ds_section = self._render_list("Major Data Stores", data_stores)
        if ds_section:
            parts.append(ds_section)

        # 6. Outputs -----------------------------------------------------------
        outputs = self._first_list(architecture_json, "outputs")
        out_section = self._render_list("Outputs", outputs)
        if out_section:
            parts.append(out_section)

        # 7. High-level Relationships ------------------------------------------
        relationships = self._first_list(
            architecture_json, "important_relationships", "relationships"
        )
        rel_section = self._render_relationships(relationships)
        if rel_section:
            parts.append(rel_section)

        result = "\n".join(parts).strip()
        return result if result else "No architecturally significant concepts found."

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _first_value(self, d: dict, *keys: str) -> str:
        """Return the first non-empty string value found for any of *keys*."""
        for key in keys:
            val = d.get(key)
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    def _first_list(self, d: dict, *keys: str) -> list:
        """Return the first non-empty list found for any of *keys*."""
        for key in keys:
            val = d.get(key)
            if isinstance(val, list) and val:
                return val
        return []

    def _is_allowed(self, name: str) -> bool:
        """Return True if *name* is architecturally significant.

        A name is rejected if:
        - It is empty or shorter than 2 characters.
        - Its lowercased form contains any of the exclusion keywords.
        - Its lowercased form matches any hallucination-guard entry exactly.
        """
        if not name or len(name.strip()) < 2:
            return False

        lower = name.strip().lower()

        # Exact match against hallucination guard list
        if lower in _HALLUCINATION_GUARD:
            return False

        # Substring match against exclusion keywords
        for kw in _EXCLUDED_KEYWORDS:
            if kw in lower:
                return False

        return True

    def _render_list(self, title: str, items: list) -> str:
        """Render *items* as a named markdown section.

        Handles both string items and dict items (with ``name`` and optional
        ``description`` keys). Items that fail the ``_is_allowed`` check are
        silently dropped. Returns an empty string if no items survive filtering.
        """
        if not items:
            return ""

        lines = [f"## {title}"]
        for item in items:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                if not self._is_allowed(name):
                    continue
                desc = str(item.get("description", "")).strip()
                lines.append(f"- {name}: {desc}" if desc else f"- {name}")
            elif isinstance(item, str):
                name = item.strip()
                if self._is_allowed(name):
                    lines.append(f"- {name}")

        # Only emit the section if there is at least one item under the title
        if len(lines) > 1:
            lines.append("")
            return "\n".join(lines)
        return ""

    def _render_relationships(self, relationships: list) -> str:
        """Render the high-level relationships section.

        Both endpoints of every relationship must pass ``_is_allowed`` — this
        prevents implementation-level services from appearing as participants
        in the relationship graph even if they slipped into the JSON.
        """
        if not relationships:
            return ""

        lines = ["## High-level Relationships"]
        for rel in relationships:
            if isinstance(rel, dict):
                source = str(rel.get("source", "")).strip()
                target = str(rel.get("target", "")).strip()
                if not (self._is_allowed(source) and self._is_allowed(target)):
                    continue
                rel_type = str(rel.get("type", "interacts with")).strip()
                desc = str(rel.get("description", "")).strip()
                entry = f"- {source} --[{rel_type}]--> {target}"
                if desc:
                    entry += f": {desc}"
                lines.append(entry)
            elif isinstance(rel, str) and rel.strip():
                lines.append(f"- {rel.strip()}")

        if len(lines) > 1:
            lines.append("")
            return "\n".join(lines)
        return ""
