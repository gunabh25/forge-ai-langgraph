"""Layer Assignment (Workstream 2).

Implements deterministic hierarchical layering.
Ensures Actors -> External Systems (Ingest) -> Domain -> External Systems (Downstream) -> Databases
and minimizes backward edges across the graph.
"""

from __future__ import annotations

from typing import List, Set

from agents.uml_generator.graph_model import DirectedGraph, GraphNode, GraphEdge
from config.logging import get_logger

logger = get_logger("agents.uml_generator.layer_assignment")


class LayerAssigner:
    """Assigns nodes to discrete layers (Y-coordinates in hierarchy)."""
    
    @classmethod
    def assign_layers(cls, graph: DirectedGraph) -> None:
        """Assign every node in the graph to a layer index (0..4)."""
        cls._break_cycles(graph)
        
        # We enforce a strict 5-layer system based on the Component Diagram schema.
        # Layer 0: Actors
        # Layer 1: Ingest External Systems
        # Layer 2: Domain (Packages, Capabilities)
        # Layer 3: Downstream External Systems
        # Layer 4: Databases
        
        actors = [n for n in graph.nodes.values() if n.node_type == "actor"]
        databases = [n for n in graph.nodes.values() if n.node_type == "database"]
        ext_systems = [n for n in graph.nodes.values() if n.node_type == "external_system"]
        domain_nodes = [n for n in graph.nodes.values() if n.node_type in ("package", "capability")]
        
        # 1. Actors always in Layer 0
        for n in actors:
            n.layer = 0
            
        # 2. Databases always in Layer 4
        for n in databases:
            n.layer = 4
            
        # 3. Domain Nodes always in Layer 2
        for n in domain_nodes:
            n.layer = 2
            
        # 4. External Systems: classify as Ingest (Layer 1) or Downstream (Layer 3)
        # Ingest = connected to actor OR has mostly outgoing edges to domain
        actor_ids = {a.id for a in actors}
        
        for ext in ext_systems:
            in_edges = graph.get_in_edges(ext.id)
            out_edges = graph.get_out_edges(ext.id)
            
            connected_to_actor = any((e.source_id in actor_ids or e.target_id in actor_ids) for e in (in_edges + out_edges))
            
            if connected_to_actor or len(out_edges) >= len(in_edges):
                ext.layer = 1
            else:
                ext.layer = 3

    @classmethod
    def _break_cycles(cls, graph: DirectedGraph) -> None:
        """Mark edges as 'is_backward=True' to break cycles in the DAG."""
        visited: Set[str] = set()
        recursion_stack: Set[str] = set()
        
        # Process nodes in deterministic order
        sorted_nodes = sorted(graph.nodes.keys())
        
        def dfs(node_id: str):
            visited.add(node_id)
            recursion_stack.add(node_id)
            
            out_edges = sorted(graph.get_out_edges(node_id), key=lambda e: e.target_id)
            for edge in out_edges:
                target_id = edge.target_id
                if target_id in recursion_stack:
                    edge.is_backward = True
                elif target_id not in visited:
                    dfs(target_id)
            
            recursion_stack.remove(node_id)

        for node_id in sorted_nodes:
            if node_id not in visited:
                dfs(node_id)
