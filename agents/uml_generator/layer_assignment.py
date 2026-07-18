"""Layer Assignment (Workstream 2).

Implements deterministic hierarchical layering driven by Business Flow (Phase 9.13).
Ensures primary flow is laid out sequentially while positioning dependencies effectively.
"""

from __future__ import annotations

from typing import List, Set

from agents.uml_generator.graph_model import DirectedGraph, GraphNode, GraphEdge
from agents.uml_generator.business_flow_layout import BusinessFlowAnalyzer
from config.logging import get_logger

logger = get_logger("agents.uml_generator.layer_assignment")


class LayerAssigner:
    """Assigns nodes to discrete layers (Y-coordinates in hierarchy)."""
    
    @classmethod
    def assign_layers(cls, graph: DirectedGraph) -> None:
        """Assign every node in the graph to a dynamic layer index (0..N)."""
        cls._break_cycles(graph)
        
        actors = sorted([n for n in graph.nodes.values() if n.node_type == "actor"], key=lambda n: n.id)
        databases = sorted([n for n in graph.nodes.values() if n.node_type == "database"], key=lambda n: n.id)
        ext_systems = sorted([n for n in graph.nodes.values() if n.node_type == "external_system"], key=lambda n: n.id)
        domain_nodes = sorted([n for n in graph.nodes.values() if n.node_type in ("package", "capability")], key=lambda n: n.id)
        
        # 1. Get Primary Backbone
        primary_path = BusinessFlowAnalyzer.compute_primary_path(graph)
        
        # 2. Assign Backbone Layers (Starts at 1 or 0)
        layer_counter = 0
        
        if actors:
            for actor in actors:
                actor.layer = 0
            layer_counter = 1
        
        max_layer = layer_counter

        for node_id in primary_path:
            node = graph.get_node(node_id)
            if node and node.layer == -1: # skip if already assigned (e.g. actor)
                node.layer = layer_counter
                layer_counter += 1
                max_layer = max(max_layer, node.layer)

        # 3. Assign remaining capabilities
        unassigned_caps = [n for n in domain_nodes if n.layer == -1]
        
        def get_max_parent_layer(n_id: str, visited: Set[str]) -> int:
            if n_id in visited: return 0
            visited.add(n_id)
            node = graph.get_node(n_id)
            if node and node.layer != -1:
                return node.layer
            
            max_l = 0
            for edge in graph.get_in_edges(n_id):
                if not edge.is_backward:
                    max_l = max(max_l, get_max_parent_layer(edge.source_id, visited))
            return max_l

        for cap in unassigned_caps:
            l = get_max_parent_layer(cap.id, set())
            cap.layer = l + 1
            max_layer = max(max_layer, cap.layer)
            
        # 4. External Systems
        actor_ids = {a.id for a in actors}
        for ext in ext_systems:
            if ext.layer != -1:
                continue
            in_edges = graph.get_in_edges(ext.id)
            out_edges = graph.get_out_edges(ext.id)
            connected_to_actor = any((e.source_id in actor_ids or e.target_id in actor_ids) for e in (in_edges + out_edges))
            
            if connected_to_actor or len(out_edges) >= len(in_edges):
                ext.layer = 1
            else:
                ext.layer = max_layer + 1

        max_layer = max(max_layer, max((n.layer for n in ext_systems), default=max_layer))

        # 5. Databases
        for db in databases:
            in_edges = graph.get_in_edges(db.id)
            if in_edges:
                owner_id = in_edges[0].source_id
                owner = graph.get_node(owner_id)
                db.layer = owner.layer + 1 if owner else max_layer + 1
            else:
                db.layer = max_layer + 1
            max_layer = max(max_layer, db.layer)

        # Store dynamically computed max layer
        graph.max_layer = max_layer

    @classmethod
    def _break_cycles(cls, graph: DirectedGraph) -> None:
        """Mark edges as 'is_backward=True' to break cycles in the DAG."""
        visited: Set[str] = set()
        recursion_stack: Set[str] = set()
        
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
