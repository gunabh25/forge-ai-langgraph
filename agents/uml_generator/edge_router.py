"""Edge Routing (Workstream 6).

Computes directional routing hints for PlantUML edges based on the final
logical coordinates and hierarchical layering of the graph.
"""

from __future__ import annotations

from typing import Dict, Tuple, List, Optional

from agents.uml_generator.graph_model import DirectedGraph
from config.logging import get_logger

logger = get_logger("agents.uml_generator.edge_router")


class EdgeRouter:
    """Computes explicit edge routing directions (-up->, -down->, -left->, -right->)."""
    
    @classmethod
    def route_edges(cls, graph: DirectedGraph, primary_path: Optional[List[str]] = None) -> Dict[Tuple[str, str], str]:
        """Compute directional routing hints based on topological positions."""
        routing_hints: Dict[Tuple[str, str], str] = {}
        
        primary_edges = set()
        if primary_path:
            for i in range(len(primary_path) - 1):
                primary_edges.add((primary_path[i], primary_path[i+1]))
        
        # We assume Top-To-Bottom flow based on the 5-layer system.
        
        for edge in graph.edges:
            src = graph.get_node(edge.source_id)
            tgt = graph.get_node(edge.target_id)
            
            pair = (edge.source_id, edge.target_id)
            
            if not src or not tgt:
                routing_hints[pair] = edge.routing_hint
                continue

            if tgt.node_type == "database":
                hint = "-down->"
            elif src.layer < tgt.layer:
                hint = "-down->"
            elif src.layer > tgt.layer:
                hint = "-up->"
            else:
                if src.x < tgt.x:
                    hint = "-right->"
                elif src.x > tgt.x:
                    hint = "-left->"
                else:
                    hint = "-right->"
            
            # Preserve primary path visual continuity
            if pair in primary_edges:
                hint = hint.replace("->", "[bold]->")
            
            edge.routing_hint = hint
            routing_hints[pair] = hint
            
        return routing_hints
