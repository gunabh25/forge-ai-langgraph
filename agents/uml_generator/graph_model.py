"""Enterprise Graph Model for Layout Computations.

Transforms the Canonical Diagram into a formalized Directed Acyclic Graph (DAG)
for mathematical layout optimization using Sugiyama-style algorithms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional

from schemas.canonical_diagram import ComponentDiagramCanonical


@dataclass
class GraphNode:
    id: str
    node_type: str  # "actor", "external_system", "capability", "package", "database"
    name: str
    parent_package_id: Optional[str] = None
    width: float = 1.0
    height: float = 1.0
    
    # Layering
    layer: int = -1
    order: int = -1
    
    # Coordinate Assignment
    x: float = 0.0
    y: float = 0.0


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    label: str = ""
    is_backward: bool = False
    
    # Routing Hints
    routing_hint: str = "-->"


class DirectedGraph:
    """Mathematical graph representation of the Canonical Diagram."""
    def __init__(self, canonical_diagram: ComponentDiagramCanonical):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.max_layer: int = 4
        self._build_graph(canonical_diagram)

    def _build_graph(self, diagram: ComponentDiagramCanonical) -> None:
        # Build Nodes
        for actor in diagram.actors:
            self.nodes[actor.id] = GraphNode(id=actor.id, node_type="actor", name=actor.name)
            
        for ext in diagram.external_systems:
            self.nodes[ext.id] = GraphNode(id=ext.id, node_type="external_system", name=ext.name)
            
        for db in diagram.databases:
            self.nodes[db.id] = GraphNode(id=db.id, node_type="database", name=db.name)
            
        for pkg in diagram.business_packages:
            self.nodes[pkg.id] = GraphNode(id=pkg.id, node_type="package", name=pkg.name)
            for cap_id in pkg.capability_ids:
                cap = diagram.get_element_by_id(cap_id)
                if cap:
                    self.nodes[cap.id] = GraphNode(id=cap.id, node_type="capability", name=cap.name, parent_package_id=pkg.id)

        # Standalone capabilities
        packaged_caps = set(n.id for n in self.nodes.values() if n.parent_package_id is not None)
        for cap in diagram.business_capabilities:
            if cap.id not in packaged_caps:
                self.nodes[cap.id] = GraphNode(id=cap.id, node_type="capability", name=cap.name)

        # Build Edges
        for rel in diagram.relationships:
            if rel.source_id in self.nodes and rel.target_id in self.nodes:
                self.edges.append(GraphEdge(
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                    label=rel.label or "",
                    routing_hint=rel.direction or "-->"
                ))

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self.nodes.get(node_id)
        
    def get_out_edges(self, node_id: str) -> List[GraphEdge]:
        return [e for e in self.edges if e.source_id == node_id]

    def get_in_edges(self, node_id: str) -> List[GraphEdge]:
        return [e for e in self.edges if e.target_id == node_id]
        
    def get_layer_nodes(self, layer: int) -> List[GraphNode]:
        return sorted([n for n in self.nodes.values() if n.layer == layer], key=lambda x: x.order)
