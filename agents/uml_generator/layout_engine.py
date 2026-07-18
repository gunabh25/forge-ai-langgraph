"""Deterministic Layout Engine (Phase 10.0 Orchestrator).

Orchestrates the 6-stage mathematical graph drawing pipeline:
1. Graph Model
2. Layer Assignment
3. Crossing Minimization
4. Node Ordering
5. Coordinate Assignment
6. Edge Routing
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from pydantic import BaseModel, Field

from schemas.canonical_diagram import ComponentDiagramCanonical

from agents.uml_generator.graph_model import DirectedGraph
from agents.uml_generator.layer_assignment import LayerAssigner
from agents.uml_generator.crossing_optimizer import CrossingOptimizer
from agents.uml_generator.node_ordering import NodeOrderer
from agents.uml_generator.coordinate_assignment import CoordinateAssigner
from agents.uml_generator.edge_router import EdgeRouter
from agents.uml_generator.readability_optimizer import ReadabilityOptimizer
from config.logging import get_logger

logger = get_logger("agents.uml_generator.layout_engine")


# ---------------------------------------------------------------------------
# Layer & Topology Models
# ---------------------------------------------------------------------------

class LayerAssignment(BaseModel):
    """Assignment of diagram elements into spatial layers."""
    layer_0_actors: List[str] = Field(default_factory=list)
    layer_1_ext_ingest: List[str] = Field(default_factory=list)
    layer_2_packages: List[str] = Field(default_factory=list)
    layer_2_capabilities: List[str] = Field(default_factory=list)
    layer_3_ext_downstream: List[str] = Field(default_factory=list)
    layer_4_databases: List[str] = Field(default_factory=list)
    element_layer_map: Dict[str, int] = Field(default_factory=dict)


class EngineLayoutResult(BaseModel):
    """Complete computed spatial layout result for a canonical component diagram."""
    direction_directive: str = Field("top to bottom direction")
    layers: LayerAssignment
    formatted_arrows: Dict[Tuple[str, str], str] = Field(default_factory=dict)
    hidden_alignment_edges: List[str] = Field(default_factory=list)
    dynamic_skinparams: List[str] = Field(default_factory=list)
    readability_metrics: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Deterministic Layout Engine Implementation
# ---------------------------------------------------------------------------

class DeterministicLayoutEngine:
    """Topology-aware spatial layout orchestrator for PlantUML diagram rendering."""

    @classmethod
    def compute_component_layout(cls, diagram: ComponentDiagramCanonical) -> EngineLayoutResult:
        """Compute full spatial layout using Sugiyama-style hierarchical graph layout."""
        
        # 1. Graph Model
        graph = DirectedGraph(diagram)
        
        # 2. Layer Assignment
        LayerAssigner.assign_layers(graph)
        
        # 3. Crossing Minimization
        CrossingOptimizer.optimize_crossings(graph)
        
        # 4. Node Ordering
        NodeOrderer.finalize_ordering(graph)
        
        # 5. Coordinate Assignment
        CoordinateAssigner.assign_coordinates(graph)
        
        # 6. Edge Routing
        routing_hints = EdgeRouter.route_edges(graph)
        
        # Generate Hidden Alignment Edges to enforce coordinates (Phase 9.8)
        hidden_alignment_edges = []
        for i in range(5):
            layer_nodes = sorted([n for n in graph.get_layer_nodes(i) if n.node_type != "package"], key=lambda n: n.x)
            for j in range(len(layer_nodes) - 1):
                hidden_alignment_edges.append(f"{layer_nodes[j].id} -[hidden]right-> {layer_nodes[j+1].id}")
        
        # Force databases directly below their first consumer
        for db in [n for n in graph.get_layer_nodes(4) if n.node_type == "database"]:
            in_edges = graph.get_in_edges(db.id)
            if in_edges:
                hidden_alignment_edges.append(f"{in_edges[0].source_id} -[hidden]down-> {db.id}")

        # Convert internal graph layout state back to EngineLayoutResult
        layers = LayerAssignment(
            layer_0_actors=[n.id for n in graph.get_layer_nodes(0) if n.node_type == "actor"],
            layer_1_ext_ingest=[n.id for n in graph.get_layer_nodes(1) if n.node_type == "external_system"],
            layer_2_packages=[n.id for n in graph.get_layer_nodes(2) if n.node_type == "package"],
            layer_2_capabilities=[n.id for n in graph.get_layer_nodes(2) if n.node_type == "capability"],
            layer_3_ext_downstream=[n.id for n in graph.get_layer_nodes(3) if n.node_type == "external_system"],
            layer_4_databases=[n.id for n in graph.get_layer_nodes(4) if n.node_type == "database"],
            element_layer_map={n.id: n.layer for n in graph.nodes.values()}
        )
        
        # Provide readability params
        ranksep, nodesep = ReadabilityOptimizer.compute_adaptive_spacing(diagram)
        dynamic_skinparams = [
            f"skinparam nodesep {nodesep}",
            f"skinparam ranksep {ranksep}",
            "skinparam sameClassWidth true",
            "skinparam maxMessageSize 100",
            "skinparam ArrowThickness 1.5",
            "skinparam defaultTextAlignment center",
        ]
        
        metrics = {
            "layout_cost": cls._calculate_layout_cost(graph),
            "total_relationships": len(diagram.relationships),
        }
        
        return EngineLayoutResult(
            direction_directive="top to bottom direction",
            layers=layers,
            formatted_arrows=routing_hints,
            hidden_alignment_edges=hidden_alignment_edges,
            dynamic_skinparams=dynamic_skinparams,
            readability_metrics=metrics,
        )

    @classmethod
    def _calculate_layout_cost(cls, graph: DirectedGraph) -> float:
        """Evaluate Workstream 10 layout cost function."""
        layers_map = {i: graph.get_layer_nodes(i) for i in range(5)}
        crossings = CrossingOptimizer.count_crossings(graph, layers_map)
        
        cost = (10 * crossings)
        return float(cost)
