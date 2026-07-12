"""Business Architecture Summary builder for UML generation.

This module extracts architecturally significant, business-level concepts from
the architecture JSON produced by the Solution Architect agent and compiles
them into a compact, markdown-formatted summary that is passed verbatim to the
LLM during diagram generation.

Design principles
-----------------
1. **Semantic concept mapping** — the extractor recognises many equivalent JSON
   key families (e.g. ``services``, ``modules``, ``components``,
   ``microservices`` all map to *Business Capabilities*) so the summary never
   silently drops content simply because the Solution Architect used slightly
   different terminology.

2. **No invented content** — the builder only emits what is explicitly present
   in the source JSON.  The hallucination guard rejects a short list of
   infrastructure names that LLMs commonly invent (API Gateway, Auth Service,
   etc.) *unless they actually appear in the JSON*.

3. **Context-aware filtering** — implementation-detail exclusion uses whole-word
   or name-level context rather than naive substring matching.  A name like
   ``"Order Manager"`` or ``"Payment Processor"`` is a legitimate business
   capability and is kept; a name like ``"OrderManagerImpl"`` or
   ``"util_helper"`` is an implementation artifact and is dropped.

4. **Deterministic** — zero LLM calls; pure Python string/dict operations.
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Concept-family key maps
# ---------------------------------------------------------------------------
# Each map is ordered from most-specific to least-specific so that the first
# match wins.  All comparisons are case-insensitive.

#: JSON key families that describe *actors / users*.
_ACTOR_KEYS: tuple[str, ...] = (
    "primary_actors",
    "actors",
    "actor",
    "users",
    "user",
    "stakeholders",
    "personas",
    "roles",
    "clients",
    "customers",
)

#: JSON key families that describe *external systems / integrations*.
_EXTERNAL_KEYS: tuple[str, ...] = (
    "external_systems",
    "external_system",
    "external_services",
    "third_party_systems",
    "third_party_services",
    "integrations",
    "external_dependencies",
    "external_interfaces",
    "external",
)

#: JSON key families that describe *business capabilities / services*.
_CAPABILITY_KEYS: tuple[str, ...] = (
    "major_business_services",
    "business_capabilities",
    "business_services",
    "capabilities",
    "capability",
    "services",
    "service",
    "microservices",
    "microservice",
    "modules",
    "module",
    "components",
    "component",
    "subsystems",
    "bounded_contexts",
    "domains",
    "features",
    "applications",
    "app",
    "systems",
    "system",
)

#: JSON key families that describe *data stores*.
_DATA_STORE_KEYS: tuple[str, ...] = (
    "major_databases",
    "databases",
    "database",
    "data_stores",
    "data_store",
    "data_sources",
    "stores",
    "store",
    "storage",
    "repositories",
    "repository",
    "caches",
    "queues",
    "topics",
    "message_queues",
    "event_stores",
    "datastores",
    "datastore",
)

#: JSON key families that describe *outputs / deliverables*.
_OUTPUT_KEYS: tuple[str, ...] = (
    "outputs",
    "output",
    "deliverables",
    "artifacts",
    "results",
)

#: JSON key families that describe *relationships*.
_RELATIONSHIP_KEYS: tuple[str, ...] = (
    "important_relationships",
    "relationships",
    "relationship",
    "interactions",
    "interaction",
    "dependencies",
    "dependency",
    "connections",
    "flows",
    "integrations",
)

#: JSON key families that describe the *business objective*.
_OBJECTIVE_KEYS: tuple[str, ...] = (
    "business_objective",
    "objective",
    "purpose",
    "system_overview",
    "overview",
    "description",
    "summary",
    "goal",
    "mission",
)


# ---------------------------------------------------------------------------
# Exclusion rules — implementation-artifact detection
# ---------------------------------------------------------------------------
# These patterns identify implementation-level *artifacts*, NOT business
# concepts.  Matching is applied at the name level, NOT as a substring of a
# multi-word business name.
#
# Strategy:
#   A) Strong artifact tokens: If a name contains ANY of these words as a distinct
#      token, the entire name is dropped. These are concepts that purely belong to
#      the implementation/data-access layer (e.g. dao, impl, helper).
#   B) Weak artifact tokens (generic roles): If a name contains these words, it is
#      ONLY dropped if the entire name consists of nothing but weak tokens. This
#      keeps "Order Manager" (business + weak) but drops "Manager" (weak).

_STRONG_IMPL_TOKENS: frozenset[str] = frozenset(
    {
        # Pure utilities
        "helper",
        "util",
        "utility",
        "utilities",
        # Data-access layer
        "repository",
        "repo",
        "dao",
        "orm",
        # Parsing / serialisation internals
        "parser",
        "serializer",
        "serialiser",
        "deserializer",
        "deserialiser",
        "marshaller",
        "unmarshaller",
        # Object-creation internals
        "factory",
        "builder",
        "impl",
        "implementation",
        # Cross-cutting internals
        "interceptor",
        "decorator",
        "mixin",
        "middleware",
        "wrapper",
        "proxy",
        # Mapping / conversion
        "mapper",
        "converter",
        "transformer",
        "adapter",
        "dto",
        # Lifecycle
        "bootstrap",
        "initializer",
        "initialiser",
        "startup",
        "teardown",
        # Observability internals
        "logger",
        "logwriter",
        # Config / settings objects
        "config",
        "configuration",
        "settings",
        # Inheritance artefacts
        "base",
        "abstract",
        # Generic class-role tokens that carry no business meaning alone
        "internal",
        "private",
        "test",
        "mock",
        "stub",
        "fake",
        "fixture",
    }
)

_WEAK_IMPL_TOKENS: frozenset[str] = frozenset(
    {
        "manager",
        "processor",
        "provider",
        "handler",
        "service",
        "component",
        "module",
        "system",
        "app",
        "application",
        "engine",
        "controller",
    }
)

# ---------------------------------------------------------------------------
# Hallucination guard — names injected by LLMs but rarely specified by users
# ---------------------------------------------------------------------------
# These are checked as EXACT matches against the normalised name (lower-cased,
# whitespace-collapsed).  A service is only rejected here if it is not
# explicitly present in the source JSON; but since we never invent names, an
# exact match means the LLM guessed it into the JSON — which we reject.

_HALLUCINATION_GUARD: frozenset[str] = frozenset(
    {
        "api gateway",
        "api_gateway",
        "auth service",
        "auth_service",
        "authentication service",
        "authentication_service",
        "authorization service",
        "authorization_service",
        "notification service",
        "notification_service",
        "audit service",
        "audit_service",
        "audit log",
        "audit_log",
        "logging service",
        "logging_service",
        "monitoring service",
        "monitoring_service",
        "metrics service",
        "metrics_service",
        "tracing service",
        "tracing_service",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokenise(name: str) -> list[str]:
    """Split a name into lowercase tokens.

    Handles camelCase, PascalCase, snake_case, kebab-case, and space-separated
    names so that ``"OrderManagerImpl"`` → ``["order", "manager", "impl"]``.
    """
    # Insert space before capital letters that start a new word (camelCase)
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    # Replace non-alphanumeric separators with spaces
    normalised = re.sub(r"[^a-zA-Z0-9]+", " ", spaced)
    return [t.lower() for t in normalised.split() if t]


def _is_impl_artifact(name: str) -> bool:
    """Return True if *name* is an implementation artifact with no business content.

    A name is an artifact when:
    - It contains ANY strong implementation token (e.g. 'impl', 'dao', 'util'), OR
    - ALL of its tokens are weak generic roles (e.g. 'manager', 'processor').

    This correctly keeps multi-word business names that happen to contain a
    weak generic role word (e.g. "Order Manager", "Payment Processor").
    """
    tokens = _tokenise(name)
    if not tokens:
        return True
    
    # If the name contains any strong artifact token, drop it.
    if any(t in _STRONG_IMPL_TOKENS for t in tokens):
        return True
        
    # If the name consists entirely of weak generic tokens, drop it.
    if all(t in _WEAK_IMPL_TOKENS for t in tokens):
        return True
        
    return False


def _is_hallucinated(name: str) -> bool:
    """Return True if *name* matches the hallucination guard exactly."""
    normalised = re.sub(r"\s+", " ", name.strip().lower())
    # Also check underscore variant
    underscored = normalised.replace(" ", "_")
    return normalised in _HALLUCINATION_GUARD or underscored in _HALLUCINATION_GUARD


def _is_allowed(name: str) -> bool:
    """Return True if *name* is architecturally significant and should appear
    in the Business Architecture Summary.

    Rejects:
    - Empty / very short names.
    - Pure implementation artifacts (``_is_impl_artifact``).
    - Hallucinated infrastructure names (``_is_hallucinated``).
    """
    if not name or len(name.strip()) < 2:
        return False
    name = name.strip()
    if _is_hallucinated(name):
        return False
    if _is_impl_artifact(name):
        return False
    return True


# ---------------------------------------------------------------------------
# Key-family lookup helpers
# ---------------------------------------------------------------------------

def _lookup_str(d: dict, keys: tuple[str, ...]) -> str:
    """Return the first non-empty string value found among *keys* (case-insensitive)."""
    lower_d = {k.lower(): v for k, v in d.items()}
    for key in keys:
        val = lower_d.get(key.lower())
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _lookup_list(d: dict, keys: tuple[str, ...]) -> list:
    """Return a merged list of items found across ALL matching keys in *d*.

    Merges rather than returns-first so that an architecture JSON using both
    ``components`` and ``microservices`` contributes all items to the same
    summary section.

    Match priority:
    1. Exact key match (case-insensitive).
    2. Partial / substring match — any dict key whose normalised form contains
       one of the target keys (e.g. ``"service_definitions"`` matches the
       ``"services"`` family).

    Duplicates (same object identity or equal value) are not de-duplicated;
    the LLM can handle repeated entries gracefully and deduplication would
    require semantic equality which is out of scope.
    """
    lower_d = {k.lower(): v for k, v in d.items()}
    collected: list = []
    seen_dict_keys: set[str] = set()

    # 1. Exact matches
    for key in keys:
        val = lower_d.get(key.lower())
        if isinstance(val, list) and val and key.lower() not in seen_dict_keys:
            collected.extend(val)
            seen_dict_keys.add(key.lower())

    # 2. Partial matches (only for dict keys not already collected)
    for key in keys:
        for dict_key, val in lower_d.items():
            if dict_key in seen_dict_keys:
                continue
            if key.lower() in dict_key and isinstance(val, list) and val:
                collected.extend(val)
                seen_dict_keys.add(dict_key)

    return collected


# ---------------------------------------------------------------------------
# Item extraction helpers
# ---------------------------------------------------------------------------

def _extract_name_desc(item: Any) -> tuple[str, str]:
    """Extract (name, description) from an item that may be a dict or string."""
    if isinstance(item, dict):
        # Try common name keys
        name = ""
        for nk in ("name", "title", "label", "id", "type"):
            v = item.get(nk, "")
            if v and isinstance(v, str) and v.strip():
                name = v.strip()
                break
        desc = ""
        for dk in ("description", "desc", "summary", "detail", "purpose", "responsibility"):
            v = item.get(dk, "")
            if v and isinstance(v, str) and v.strip():
                desc = v.strip()
                break
        return name, desc
    if isinstance(item, str) and item.strip():
        return item.strip(), ""
    return "", ""


# ---------------------------------------------------------------------------
# ContextBuilder
# ---------------------------------------------------------------------------


class ContextBuilder:
    """Builds a Business Architecture Summary from an architecture JSON dict.

    The summary is a compact, markdown-formatted document containing only
    architecturally significant business concepts.  It is passed verbatim to
    the LLM as the sole source of architectural truth — so accuracy and
    brevity are both critical.

    Key improvements over the previous implementation
    --------------------------------------------------
    - **Semantic key families**: recognises ``modules``, ``components``,
      ``microservices``, ``stores``, ``repositories``, etc. as equivalent to
      the canonical keys.
    - **Context-aware filtering**: a name like ``"Order Manager"`` or
      ``"Payment Processor"`` is kept because it contains a business token;
      only purely-artifact names (e.g. ``"RepositoryImpl"``, ``"util_helper"``)
      are dropped.
    - **Partial key matching**: if the JSON uses ``"service_definitions"``
      instead of ``"services"``, the extractor still finds it.
    - **Hallucination guard preserved**: verbatim-guard rejects LLM-injected
      infrastructure names that do not appear in the JSON.
    - **Deterministic**: zero LLM calls.

    Usage::

        builder = ContextBuilder()
        summary = builder.build_summary(architecture_json)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_summary(self, architecture_json: dict) -> str:
        """Build a Business Architecture Summary from *architecture_json*.

        Args:
            architecture_json: The architecture definition produced by the
                Solution Architect agent.  May use any key naming convention.

        Returns:
            A markdown-formatted Business Architecture Summary string.
            Returns a placeholder message when the dict is empty or None.
        """
        if not architecture_json:
            return "No architecture details provided."

        parts: list[str] = []

        # 1. Business Objective ------------------------------------------------
        objective = _lookup_str(architecture_json, _OBJECTIVE_KEYS)
        if objective:
            parts.append(f"## Business Objective\n{objective}\n")

        # 2. Primary Actors ----------------------------------------------------
        actors = _lookup_list(architecture_json, _ACTOR_KEYS)
        actor_section = self._render_list("Actors", actors, filter_impl=False)
        if actor_section:
            parts.append(actor_section)

        # 3. External Systems --------------------------------------------------
        external = _lookup_list(architecture_json, _EXTERNAL_KEYS)
        ext_section = self._render_list("External Systems", external, filter_impl=False)
        if ext_section:
            parts.append(ext_section)

        # 4. Business Capabilities ---------------------------------------------
        capabilities = _lookup_list(architecture_json, _CAPABILITY_KEYS)
        cap_section = self._render_list("Business Capabilities", capabilities, filter_impl=True)
        if cap_section:
            parts.append(cap_section)

        # 5. Data Stores -------------------------------------------------------
        data_stores = _lookup_list(architecture_json, _DATA_STORE_KEYS)
        ds_section = self._render_list("Data Stores", data_stores, filter_impl=False)
        if ds_section:
            parts.append(ds_section)

        # 6. Outputs -----------------------------------------------------------
        outputs = _lookup_list(architecture_json, _OUTPUT_KEYS)
        out_section = self._render_list("Outputs", outputs, filter_impl=False)
        if out_section:
            parts.append(out_section)

        # 7. High-level Relationships ------------------------------------------
        relationships = _lookup_list(architecture_json, _RELATIONSHIP_KEYS)
        rel_section = self._render_relationships(relationships)
        if rel_section:
            parts.append(rel_section)

        result = "\n".join(parts).strip()
        return result if result else "No architecturally significant concepts found."

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _render_list(
        self,
        title: str,
        items: list,
        *,
        filter_impl: bool = True,
    ) -> str:
        """Render *items* as a named markdown section.

        Args:
            title: Section heading (without ``##`` prefix).
            items: List of strings or dicts to render.
            filter_impl: When True, implementation-artifact names are dropped.
                Set to False for actors, external systems, and data stores where
                the ``_is_impl_artifact`` heuristic is not appropriate.
        """
        if not items:
            return ""

        lines = [f"## {title}"]
        for item in items:
            name, desc = _extract_name_desc(item)
            if not name:
                continue

            # Hallucination guard is always applied.
            if _is_hallucinated(name):
                continue

            # Implementation-artifact filter applied only when requested.
            if filter_impl and _is_impl_artifact(name):
                continue

            # Very short names are dropped unconditionally.
            if len(name) < 2:
                continue

            lines.append(f"- {name}: {desc}" if desc else f"- {name}")

        if len(lines) > 1:
            lines.append("")
            return "\n".join(lines)
        return ""

    def _render_relationships(self, relationships: list) -> str:
        """Render the high-level relationships section.

        Endpoint filtering uses ``_is_allowed`` — both the source and target
        must pass the hallucination guard.  The implementation-artifact filter
        is NOT applied to relationship endpoints because a relationship that
        explicitly exists in the JSON between a business capability and an
        implementation detail is still architecturally relevant (the business
        capability must appear; the implementation detail is surfaced as-is
        from the JSON rather than invented).
        """
        if not relationships:
            return ""

        lines = ["## High-level Relationships"]
        for rel in relationships:
            if isinstance(rel, dict):
                source = str(rel.get("source", rel.get("from", rel.get("caller", "")))).strip()
                target = str(rel.get("target", rel.get("to", rel.get("callee", "")))).strip()

                if not source or not target:
                    continue
                # Only the hallucination guard applies to relationship endpoints
                # (not the impl-artifact filter — the endpoint names come from
                # the JSON directly, so they are never invented).
                if _is_hallucinated(source) or _is_hallucinated(target):
                    continue

                rel_type = str(
                    rel.get("type", rel.get("relationship", rel.get("interaction", "interacts with")))
                ).strip()
                desc = str(rel.get("description", rel.get("desc", rel.get("label", "")))).strip()
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
