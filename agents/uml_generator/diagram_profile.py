"""Data-driven per-diagram-type profiles for UML generation.

Each profile drives how ``PromptBuilder`` frames the generation request for
the LLM. Adding a new diagram type requires only a new entry in
``DIAGRAM_PROFILES`` — no function or template changes are needed.

Profile fields
--------------
audience : str
    Who the diagram is written for (e.g. "Senior Software Architect").
abstraction : str
    The expected abstraction level (e.g. "High", "Domain", "Infrastructure").
objective : str
    One sentence describing what the diagram must communicate.
include : list[str]
    Bullet items the LLM must include.
avoid : list[str]
    Bullet items the LLM must never include.
max_note : str | None
    Optional hard constraint shown as a single line (e.g. "Maximum 8 components").
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiagramProfile:
    """Immutable profile that drives prompt rendering for one diagram type."""

    audience: str
    abstraction: str
    objective: str
    include: list[str]
    avoid: list[str]
    max_note: str | None = None


# ---------------------------------------------------------------------------
# Profile registry
# ---------------------------------------------------------------------------

DIAGRAM_PROFILES: dict[str, DiagramProfile] = {
    "component": DiagramProfile(
        audience="Senior Software Architect",
        abstraction="High — bounded contexts and external integrations only",
        objective=(
            "Show the high-level decomposition of the system into major "
            "business services, external systems, and data stores."
        ),
        include=[
            "Core business services (each representing a bounded context)",
            "External systems and third-party integrations",
            "Persistent data stores (databases, object storage)",
            "Dependency arrows labelled with the interaction verb or protocol",
            "Packages or groupings to convey domain or deployment boundaries",
            "Stereotypes: <<service>>, <<external>>, <<datastore>>",
        ],
        avoid=[
            "Repository classes, DAOs, or data-access layers",
            "Helper classes, utility modules, or shared libraries",
            "Internal implementation details (queues, caches, serializers)",
            "Framework infrastructure (middleware, interceptors)",
            "Any component that exists solely to support another component's internals",
            "Invented services not present in the architecture summary",
        ],
        max_note="Maximum 8 components. Group related capabilities when the architecture is larger.",
    ),
    "sequence": DiagramProfile(
        audience="Senior Software Architect",
        abstraction="Business workflow — service boundaries only, no internal method calls",
        objective=(
            "Illustrate the primary business flow (happy path) from initiating "
            "actor to final response, showing only service-level interactions."
        ),
        include=[
            "Primary actors (users, external systems) that initiate the flow",
            "Key domain services that participate in the core transaction",
            "Synchronous calls (→) and responses (-->) with descriptive labels",
            "Asynchronous messages (->>>) where the architecture uses event-driven communication",
            "Return values or response descriptions on reply arrows",
        ],
        avoid=[
            "Repository or data-access layer interactions (abstract behind owning service)",
            "Helper classes, utility calls, or cross-cutting concerns (logging, auth middleware)",
            "Internal method calls within a single service",
            "Error-handling paths, retries, or fallback logic",
            "Invented participants not present in the architecture summary",
        ],
        max_note="Maximum 10 participants and 20 messages.",
    ),
    "activity": DiagramProfile(
        audience="Senior Software Architect / Business Analyst",
        abstraction="Business process — steps visible to a domain expert",
        objective=(
            "Capture the main business workflow from trigger to completion, "
            "showing decision points that affect the business outcome."
        ),
        include=[
            "Start (start) and end (stop) nodes",
            "High-level business steps as action nodes",
            "Decision diamonds for critical business branching logic",
            "Swim-lanes (|LaneName|) when multiple actors own different steps",
        ],
        avoid=[
            "Implementation-level steps (database queries, HTTP calls, cache lookups)",
            "Framework or infrastructure actions",
            "More than 5 swim-lanes",
            "More than 15 action steps",
        ],
        max_note="Maximum 5 swim-lanes and 15 steps.",
    ),
    "deployment": DiagramProfile(
        audience="Senior Software Architect / DevOps Engineer",
        abstraction="Infrastructure — deployment targets and network boundaries",
        objective=(
            "Show how system components are physically or logically deployed "
            "across infrastructure nodes and the communication protocols between them."
        ),
        include=[
            "Infrastructure nodes (servers, cloud regions, containers) using node keyword",
            "Deployment artifacts mapped to their nodes",
            "Network boundaries and zones (DMZ, VPC, internal network)",
            "Communication protocols labelled on connections",
            "Data stores positioned on their hosting node",
        ],
        avoid=[
            "Source-level code artefacts (classes, methods, modules)",
            "Implementation details not visible at the infrastructure level",
            "More than 10 nodes",
        ],
        max_note="Maximum 10 nodes.",
    ),
    "class": DiagramProfile(
        audience="Senior Software Architect",
        abstraction="Domain model — key entities and their relationships",
        objective=(
            "Model the core domain entities, their attributes, and structural "
            "relationships to communicate the business data model."
        ),
        include=[
            "Core domain entities (aggregates, value objects, key entities)",
            "Associations, compositions, and inheritance relationships",
            "Key attributes that define the entity's identity or behaviour",
            "Interface definitions for publicly contracted boundaries",
        ],
        avoid=[
            "Utility or helper classes",
            "Repository or persistence classes",
            "Framework base classes",
            "Implementation-only attributes (private counters, flags)",
            "More than 12 classes",
        ],
        max_note="Maximum 12 classes.",
    ),
    "use case": DiagramProfile(
        audience="Senior Software Architect / Product Owner",
        abstraction="Functional scope — what the system does, not how",
        objective=(
            "Capture the primary actors and the high-level use cases they "
            "participate in, scoped to the system boundary."
        ),
        include=[
            "All primary actors (users and external systems) using actor keyword",
            "High-level use cases as usecase nodes",
            "Associations between actors and their use cases",
            "System boundary using a rectangle enclosing the use cases",
            "<<include>> and <<extend>> only where architecturally significant",
        ],
        avoid=[
            "Implementation-level detail inside use cases",
            "Internal system services as actors",
            "More than 6 actors",
            "More than 12 use cases",
        ],
        max_note="Maximum 6 actors and 12 use cases.",
    ),
}


def get_profile(diagram_type: str) -> DiagramProfile | None:
    """Return the profile for *diagram_type* (case-insensitive), or None."""
    return DIAGRAM_PROFILES.get(diagram_type.lower())
