"""Canonical Diagram JSON Schema Models.

Provides deterministic, provider-independent Pydantic models for architectural diagram
representation. Used as the intermediate representation between LLM architectural reasoning
and deterministic PlantUML rendering.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Base & Shared Elements (with Stable IDs)
# ---------------------------------------------------------------------------

class BaseElement(BaseModel):
    """Base architectural element with a stable unique string ID."""
    id: str = Field(..., description="Stable unique string identifier (e.g. 'actor_customer', 'cap_order_service')")
    name: str = Field(..., description="Human-readable display name")
    description: Optional[str] = Field(None, description="Brief architectural description")


class Actor(BaseElement):
    """User or external actor interacting with the system."""
    stereotype: Optional[str] = Field("actor", description="Actor stereotype")


class ExternalSystem(BaseElement):
    """External third-party system or service."""
    technology: Optional[str] = Field(None, description="Protocol or technology (e.g. 'REST API', 'OAuth2')")


class BusinessCapability(BaseElement):
    """Core business service or component capability."""
    stereotype: Optional[str] = Field(None, description="Capability stereotype")


class Database(BaseElement):
    """Database, datastore, or cache component."""
    db_type: Optional[str] = Field(None, description="Database type (e.g. 'PostgreSQL', 'Redis')")


class BusinessPackage(BaseModel):
    """Package/namespace grouping business capabilities."""
    id: str = Field(..., description="Stable package identifier (e.g. 'pkg_core')")
    name: str = Field(..., description="Package display name")
    capability_ids: List[str] = Field(
        default_factory=list,
        description="Stable IDs of business capabilities or databases inside this package"
    )


class Relationship(BaseModel):
    """Relationship between elements referenced strictly by stable source/target IDs."""
    id: Optional[str] = Field(None, description="Optional relationship ID")
    source_id: str = Field(..., description="Stable ID of source element")
    target_id: str = Field(..., description="Stable ID of target element")
    direction: str = Field("-->", description="Arrow syntax ('-->', '->', '<--', '<->', '..>')")
    label: Optional[str] = Field(None, description="Description or message label")
    protocol: Optional[str] = Field(None, description="Communication protocol")
    step_number: Optional[int] = Field(None, description="Ordered step sequence number")


class DiagramMetadata(BaseModel):
    """Metadata describing the diagram."""
    diagram_type: str = Field(..., description="Type of UML diagram ('component' or 'sequence')")
    title: Optional[str] = Field(None, description="Diagram title")
    description: Optional[str] = Field(None, description="High-level summary")
    scope: Optional[str] = Field(None, description="Architectural scope")


# ---------------------------------------------------------------------------
# Base Canonical Diagram
# ---------------------------------------------------------------------------

class BaseCanonicalDiagram(BaseModel):
    """Shared base model for canonical diagram representations."""
    metadata: DiagramMetadata
    actors: List[Actor] = Field(default_factory=list)
    external_systems: List[ExternalSystem] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)

    def all_elements(self) -> List[BaseElement]:
        """Return flat list of all elements in diagram."""
        elems: List[BaseElement] = []
        elems.extend(self.actors)
        elems.extend(self.external_systems)
        if hasattr(self, "business_capabilities"):
            elems.extend(getattr(self, "business_capabilities"))
        if hasattr(self, "databases"):
            elems.extend(getattr(self, "databases"))
        return elems

    def all_element_ids(self) -> Set[str]:
        """Return set of all element IDs defined in this diagram."""
        return {elem.id for elem in self.all_elements()}

    def get_element_by_id(self, element_id: str) -> Optional[BaseElement]:
        """Find architectural element by stable ID."""
        for elem in self.all_elements():
            if elem.id == element_id:
                return elem
        return None


# ---------------------------------------------------------------------------
# Diagram-Specific Canonical Models
# ---------------------------------------------------------------------------

class ComponentDiagramCanonical(BaseCanonicalDiagram):
    """Canonical representation of a Component Diagram."""
    business_packages: List[BusinessPackage] = Field(default_factory=list)
    business_capabilities: List[BusinessCapability] = Field(default_factory=list)
    databases: List[Database] = Field(default_factory=list)


class SequenceDiagramCanonical(BaseCanonicalDiagram):
    """Canonical representation of a Sequence Diagram."""
    business_capabilities: List[BusinessCapability] = Field(default_factory=list)
    databases: List[Database] = Field(default_factory=list)
    participants: List[str] = Field(
        default_factory=list,
        description="Explicit ordered list of participant element IDs for lifeline sequence"
    )
