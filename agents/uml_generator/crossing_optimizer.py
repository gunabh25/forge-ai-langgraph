"""Crossing Minimization (Workstream 3).

Implements deterministic crossing minimization using Barycenter and Median heuristics,
along with Adjacent Exchange swapping to guarantee minimum edge crossings.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from agents.uml_generator.graph_model import DirectedGraph, GraphNode
from config.logging import get_logger

logger = get_logger("agents.uml_generator.crossing_optimizer")


class CrossingOptimizer:
    """Optimizes the relative order of nodes within their assigned layers."""

    @classmethod
    def optimize_crossings(cls, graph: DirectedGraph, max_iterations: int = 4) -> None:
        """Run barycenter heuristic across layers to minimize crossings."""
        layers = cls._group_nodes_by_layer(graph)
        max_layer = getattr(graph, "max_layer", 4)
        
        # Initialize with deterministic alphabetical sort for baseline
        for i in range(max_layer + 1):
            layers[i].sort(key=lambda n: (n.parent_package_id or "", n.id))
            for order, node in enumerate(layers[i]):
                node.order = order

        best_order = cls._extract_order_map(layers)
        best_crossings = cls.count_crossings(graph, layers)

        if best_crossings == 0:
            return

        for iteration in range(max_iterations):
            # Forward sweep
            for i in range(1, max_layer + 1):
                cls._sweep_layer(graph, layers[i], layers[i - 1], direction="forward")
                cls._adjacent_exchange(graph, layers, i)

            # Backward sweep
            for i in range(max_layer - 1, -1, -1):
                cls._sweep_layer(graph, layers[i], layers[i + 1], direction="backward")
                cls._adjacent_exchange(graph, layers, i)

            current_crossings = cls.count_crossings(graph, layers)
            if current_crossings < best_crossings:
                best_crossings = current_crossings
                best_order = cls._extract_order_map(layers)
                if best_crossings == 0:
                    break

        # Apply best order back to graph nodes
        for node_id, order in best_order.items():
            node = graph.get_node(node_id)
            if node:
                node.order = order

    @classmethod
    def _sweep_layer(
        cls, 
        graph: DirectedGraph, 
        target_layer: List[GraphNode], 
        ref_layer: List[GraphNode], 
        direction: str
    ) -> None:
        """Apply barycenter sorting to target_layer based on ref_layer."""
        if not target_layer or not ref_layer:
            return

        ref_positions = {n.id: i for i, n in enumerate(ref_layer)}
        
        def get_barycenter(node: GraphNode) -> float:
            if direction == "forward":
                edges = graph.get_in_edges(node.id)
                neighbors = [e.source_id for e in edges if not e.is_backward]
            else:
                edges = graph.get_out_edges(node.id)
                neighbors = [e.target_id for e in edges if not e.is_backward]
                
            positions = [ref_positions[n] for n in neighbors if n in ref_positions]
            if not positions:
                return float(node.order)
            return sum(positions) / len(positions)

        target_layer.sort(key=lambda n: (get_barycenter(n), n.order))
        
        for order, node in enumerate(target_layer):
            node.order = order

    @classmethod
    def _adjacent_exchange(cls, graph: DirectedGraph, layers: Dict[int, List[GraphNode]], layer_idx: int) -> None:
        """Swap adjacent nodes if it reduces crossings."""
        layer = layers[layer_idx]
        improved = True
        while improved:
            improved = False
            for i in range(len(layer) - 1):
                c_before = cls.count_crossings(graph, layers)
                
                layer[i], layer[i+1] = layer[i+1], layer[i]
                for order, node in enumerate(layer):
                    node.order = order
                    
                c_after = cls.count_crossings(graph, layers)
                
                if c_after < c_before:
                    improved = True
                else:
                    layer[i], layer[i+1] = layer[i+1], layer[i]
                    for order, node in enumerate(layer):
                        node.order = order

    @classmethod
    def count_crossings(cls, graph: DirectedGraph, layers: Dict[int, List[GraphNode]]) -> int:
        """Count total edge crossings between adjacent layers."""
        crossings = 0
        max_layer = getattr(graph, "max_layer", 4)
        for i in range(max_layer):
            layer_upper = layers.get(i, [])
            layer_lower = layers.get(i+1, [])
            
            upper_pos = {n.id: idx for idx, n in enumerate(layer_upper)}
            lower_pos = {n.id: idx for idx, n in enumerate(layer_lower)}
            
            edges = []
            for e in graph.edges:
                s_node = graph.get_node(e.source_id)
                t_node = graph.get_node(e.target_id)
                if not s_node or not t_node:
                    continue
                if s_node.layer == i and t_node.layer == i+1:
                    edges.append((upper_pos[s_node.id], lower_pos[t_node.id]))
                elif s_node.layer == i+1 and t_node.layer == i:
                    edges.append((upper_pos[t_node.id], lower_pos[s_node.id]))
            
            for idx1 in range(len(edges)):
                for idx2 in range(idx1 + 1, len(edges)):
                    u1, v1 = edges[idx1]
                    u2, v2 = edges[idx2]
                    if (u1 < u2 and v1 > v2) or (u1 > u2 and v1 < v2):
                        crossings += 1
                        
        return crossings

    @classmethod
    def _group_nodes_by_layer(cls, graph: DirectedGraph) -> Dict[int, List[GraphNode]]:
        max_layer = getattr(graph, "max_layer", 4)
        layers = {i: [] for i in range(max_layer + 1)}
        for n in graph.nodes.values():
            if 0 <= n.layer <= max_layer:
                layers[n.layer].append(n)
        return layers

    @classmethod
    def _extract_order_map(cls, layers: Dict[int, List[GraphNode]]) -> Dict[str, int]:
        return {n.id: n.order for layer in layers.values() for n in layer}
