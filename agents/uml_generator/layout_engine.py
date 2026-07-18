"""Deterministic Layout Engine.

Calculates spatial placement layers, topology-based orientation,
edge crossing minimization, and relationship arrow routing hints for PlantUML diagrams.

Spatial Layer Architecture:
Layer 0 (Left / Top)    : Actors
Layer 1 (Center-Left)   : Ingest External Systems
Layer 2 (Center)        : Business Packages & Capabilities (Domain Layer)
Layer 3 (Center-Right)  : Downstream External Systems
Layer 4 (Bottom / Right): Databases (Data Layer)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

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
from config.logging import get_logger

logger = get_logger("agents.uml_generator.layout_engine")


# ---------------------------------------------------------------------------
# Layer & Topology Models
# ---------------------------------------------------------------------------

class LayerAssignment(BaseModel):
    """Assignment of diagram elements into spatial layers."""
    layer_0_actors: List[str] = Field(default_factory=list, description="Actor IDs (Layer 0 - Left/Top)")
    layer_1_ext_ingest: List[str] = Field(default_factory=list, description="Ingest External System IDs (Layer 1)")
    layer_2_packages: List[str] = Field(default_factory=list, description="Package IDs (Layer 2 - Center Domain)")
    layer_2_capabilities: List[str] = Field(default_factory=list, description="Standalone Capability IDs (Layer 2)")
    layer_3_ext_downstream: List[str] = Field(default_factory=list, description="Downstream External System IDs (Layer 3)")
    layer_4_databases: List[str] = Field(default_factory=list, description="Database IDs (Layer 4 - Bottom Data Layer)")
    element_layer_map: Dict[str, int] = Field(default_factory=dict, description="Map of element_id -> layer index (0..4)")


class EngineLayoutResult(BaseModel):
    """Complete computed spatial layout result for a canonical component diagram."""
    direction_directive: str = Field("top to bottom direction", description="Computed layout orientation")
    layers: LayerAssignment
    formatted_arrows: Dict[Tuple[str, str], str] = Field(default_factory=dict, description="Map of (src, tgt) -> formatted arrow hint")
    hidden_alignment_edges: List[str] = Field(default_factory=list, description="Hidden alignment edges for spatial grid")
    dynamic_skinparams: List[str] = Field(default_factory=list, description="Dynamic PlantUML skinparams for spacing")
    readability_metrics: Dict[str, Any] = Field(default_factory=dict, description="Presentation readability metrics")


# ---------------------------------------------------------------------------
# Deterministic Layout Engine Implementation
# ---------------------------------------------------------------------------

class DeterministicLayoutEngine:
    """Topology-aware spatial layout engine for PlantUML diagram rendering."""

    @classmethod
    def compute_component_layout(cls, diagram: ComponentDiagramCanonical) -> EngineLayoutResult:
        """Compute full spatial layout for a Component Diagram."""
        # 1. Analyze Topology & Determine Layout Direction
        direction_directive = cls.analyze_topology(diagram)

        # 2. Assign Spatial Layers (Actors -> Ingest Systems -> Packages/Capabilities -> Downstream Systems -> Databases)
        layers = cls.assign_layers(diagram)

        # 3. Compute Relationship Routing Hints based on layer indices
        formatted_arrows = cls.compute_routing_hints(diagram, layers, direction_directive)

        # 4. Compute Hidden Alignment Edges for spatial grid alignment
        hidden_alignment_edges = cls.compute_alignment_edges(diagram, layers, direction_directive)

        # 5. Compute Dynamic PlantUML Spacing Skinparams
        dynamic_skinparams = cls.compute_dynamic_skinparams(diagram)

        # 6. Compute Presentation Readability Metrics
        readability_metrics = cls.compute_readability_metrics(diagram, layers, formatted_arrows)

        return EngineLayoutResult(
            direction_directive=direction_directive,
            layers=layers,
            formatted_arrows=formatted_arrows,
            hidden_alignment_edges=hidden_alignment_edges,
            dynamic_skinparams=dynamic_skinparams,
            readability_metrics=readability_metrics,
        )

    @classmethod
    def analyze_topology(cls, diagram: ComponentDiagramCanonical) -> str:
        """Analyze graph depth vs breadth ratio to select layout orientation."""
        num_packages = len(diagram.business_packages)
        num_actors = len(diagram.actors)
        num_databases = len(diagram.databases)
        num_capabilities = len(diagram.business_capabilities)
        total_elements = len(diagram.all_elements())

        # If high breadth (multiple packages or many capabilities) -> Left to Right
        if num_packages >= 2 or num_capabilities >= 5 or (num_actors > 0 and num_databases > 0 and total_elements >= 6):
            return "left to right direction"
        else:
            return "top to bottom direction"

    @classmethod
    def assign_layers(cls, diagram: ComponentDiagramCanonical) -> LayerAssignment:
        """Assign all elements to spatial grid layers to minimize edge crossings."""
        element_layer_map: Dict[str, int] = {}

        # Layer 0: Actors (Left / Top)
        actors_sorted = sorted([a.id for a in diagram.actors])
        for a_id in actors_sorted:
            element_layer_map[a_id] = 0

        # Layer 4: Databases (Bottom Data Layer)
        databases_sorted = sorted([d.id for d in diagram.databases])
        for d_id in databases_sorted:
            element_layer_map[d_id] = 4

        # Classify External Systems into Ingest (Layer 1) vs Downstream (Layer 3)
        actor_ids = set(actors_sorted)
        ext_ingest: List[str] = []
        ext_downstream: List[str] = []

        for ext in sorted(diagram.external_systems, key=lambda e: e.id):
            # Check if external system is an inbound source (initiates relationships or connects to actor)
            is_inbound_source = any(r.source_id == ext.id for r in diagram.relationships) or any(
                r.source_id in actor_ids or r.target_id in actor_ids
                for r in diagram.relationships
                if r.source_id == ext.id or r.target_id == ext.id
            )
            if is_inbound_source:
                ext_ingest.append(ext.id)
                element_layer_map[ext.id] = 1
            else:
                ext_downstream.append(ext.id)
                element_layer_map[ext.id] = 3

        # Layer 2: Packages & Capabilities (Domain Layer)
        packages_sorted = sorted([p.id for p in diagram.business_packages])

        packaged_capability_ids: Set[str] = set()
        for pkg in diagram.business_packages:
            packaged_capability_ids.update(pkg.capability_ids)

        standalone_capabilities = sorted([
            c.id for c in diagram.business_capabilities
            if c.id not in packaged_capability_ids
        ])

        for p_id in packages_sorted:
            element_layer_map[p_id] = 2
        for c in diagram.business_capabilities:
            element_layer_map[c.id] = 2

        return LayerAssignment(
            layer_0_actors=actors_sorted,
            layer_1_ext_ingest=ext_ingest,
            layer_2_packages=packages_sorted,
            layer_2_capabilities=standalone_capabilities,
            layer_3_ext_downstream=ext_downstream,
            layer_4_databases=databases_sorted,
            element_layer_map=element_layer_map,
        )

    @classmethod
    def compute_routing_hints(
        cls,
        diagram: ComponentDiagramCanonical,
        layers: LayerAssignment,
        direction_directive: str,
    ) -> Dict[Tuple[str, str], str]:
        """Compute explicit directional arrow hints (-right->, -down->, etc.) per relationship."""
        formatted_arrows: Dict[Tuple[str, str], str] = {}
        is_lr = (direction_directive == "left to right direction")

        for rel in sorted(diagram.relationships, key=lambda r: (r.source_id, r.target_id)):
            pair = (rel.source_id, rel.target_id)
            direction_str = rel.direction.strip()

            # If user/LLM provided specific custom direction like `-left->` or `-up->`, preserve it
            if direction_str not in ("-->", "->"):
                formatted_arrows[pair] = direction_str
                continue

            src_layer = layers.element_layer_map.get(rel.source_id, 2)
            tgt_layer = layers.element_layer_map.get(rel.target_id, 2)

            # Rule 1: Target is Database (Layer 4) -> Always `-down->`
            if tgt_layer == 4:
                formatted_arrows[pair] = "-down->"
            # Rule 2: Source is Actor (Layer 0) -> `-right->` in LR mode, `-down->` in TB mode
            elif src_layer == 0:
                formatted_arrows[pair] = "-right->" if is_lr else "-down->"
            # Rule 3: Forward flow across layers (Layer X -> Layer Y where X < Y)
            elif src_layer < tgt_layer:
                formatted_arrows[pair] = "-right->" if is_lr else "-down->"
            # Rule 4: Feedback flow (Layer X -> Layer Y where X > Y)
            elif src_layer > tgt_layer:
                formatted_arrows[pair] = "-left->" if is_lr else "-up->"
            # Rule 5: Same layer connection (Layer X == Layer Y)
            else:
                formatted_arrows[pair] = "-down->" if is_lr else "-right->"

        return formatted_arrows

    @classmethod
    def compute_alignment_edges(
        cls,
        diagram: ComponentDiagramCanonical,
        layers: LayerAssignment,
        direction_directive: str,
    ) -> List[str]:
        """Generate hidden alignment edges (-[hidden]right->, -[hidden]down->) for spatial grid."""
        hidden_edges: List[str] = []
        is_lr = (direction_directive == "left to right direction")

        # 1. Align Actors (Layer 0) -> First Package/Capability (Layer 2)
        if layers.layer_0_actors and (layers.layer_2_packages or layers.layer_2_capabilities):
            actor_ref = layers.layer_0_actors[0]
            target_ref = layers.layer_2_packages[0] if layers.layer_2_packages else layers.layer_2_capabilities[0]
            align_dir = "right" if is_lr else "down"
            hidden_edges.append(f"{actor_ref} -[hidden]{align_dir}-> {target_ref}")

        # 2. Align Packages horizontally/vertically in Layer 2
        if len(layers.layer_2_packages) > 1:
            align_dir = "right" if is_lr else "down"
            for i in range(len(layers.layer_2_packages) - 1):
                p1, p2 = layers.layer_2_packages[i], layers.layer_2_packages[i + 1]
                hidden_edges.append(f"{p1} -[hidden]{align_dir}-> {p2}")

        # 3. Align Core Packages/Capabilities (Layer 2) -> Databases (Layer 4)
        if (layers.layer_2_packages or layers.layer_2_capabilities) and layers.layer_4_databases:
            src_ref = layers.layer_2_packages[0] if layers.layer_2_packages else layers.layer_2_capabilities[0]
            db_ref = layers.layer_4_databases[0]
            hidden_edges.append(f"{src_ref} -[hidden]down-> {db_ref}")

        # 4. Align Databases horizontally under Layer 4
        if len(layers.layer_4_databases) > 1:
            for i in range(len(layers.layer_4_databases) - 1):
                db1, db2 = layers.layer_4_databases[i], layers.layer_4_databases[i + 1]
                hidden_edges.append(f"{db1} -[hidden]right-> {db2}")

        return sorted(hidden_edges)

    @classmethod
    def topological_sort_capabilities(
        cls,
        diagram: ComponentDiagramCanonical,
        capability_ids: List[str],
    ) -> List[str]:
        """Order capabilities inside packages based on interaction flow topology."""
        cap_set = set(capability_ids)
        if len(cap_set) <= 1:
            return sorted(capability_ids)

        in_degree: Dict[str, int] = {c: 0 for c in cap_set}
        adj: Dict[str, List[str]] = {c: [] for c in cap_set}

        for rel in diagram.relationships:
            if rel.source_id in cap_set and rel.target_id in cap_set and rel.source_id != rel.target_id:
                adj[rel.source_id].append(rel.target_id)
                in_degree[rel.target_id] += 1

        # Kahn's algorithm with deterministic tie-breaking (sorted IDs)
        queue = sorted([c for c in cap_set if in_degree[c] == 0])
        sorted_caps: List[str] = []

        while queue:
            curr = queue.pop(0)
            sorted_caps.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
            queue.sort()

        # Append any remaining capabilities if cycles exist
        remaining = sorted([c for c in cap_set if c not in set(sorted_caps)])
        sorted_caps.extend(remaining)
        return sorted_caps

    @classmethod
    def compute_dynamic_skinparams(cls, diagram: ComponentDiagramCanonical) -> List[str]:
        """Compute dynamic spacing and enterprise styling skinparams based on diagram complexity."""
        num_elements = len(diagram.all_elements())
        if num_elements <= 6:
            nodesep = 35
            ranksep = 35
        elif num_elements <= 12:
            nodesep = 50
            ranksep = 50
        else:
            nodesep = 70
            ranksep = 70

        return [
            f"skinparam nodesep {nodesep}",
            f"skinparam ranksep {ranksep}",
            "skinparam padding 8",
            "skinparam ArrowThickness 1.5",
        ]

    @classmethod
    def compute_readability_metrics(
        cls,
        diagram: ComponentDiagramCanonical,
        layers: LayerAssignment,
        formatted_arrows: Dict[Tuple[str, str], str],
    ) -> Dict[str, Any]:
        """Compute presentation readability metrics."""
        total_rels = len(diagram.relationships)
        backward_edges = 0
        total_layer_span = 0

        for rel in diagram.relationships:
            src_layer = layers.element_layer_map.get(rel.source_id, 2)
            tgt_layer = layers.element_layer_map.get(rel.target_id, 2)
            span = abs(tgt_layer - src_layer)
            total_layer_span += span
            if src_layer > tgt_layer:
                backward_edges += 1

        total_caps = len(diagram.business_capabilities)
        packaged_caps = sum(len(p.capability_ids) for p in diagram.business_packages)
        package_compactness = (packaged_caps / total_caps) if total_caps > 0 else 1.0

        return {
            "total_relationships": total_rels,
            "backward_edges": backward_edges,
            "average_layer_span": (total_layer_span / total_rels) if total_rels > 0 else 0.0,
            "package_compactness": package_compactness,
        }
