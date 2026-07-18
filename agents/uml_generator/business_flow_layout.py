"""Business Flow Analyzer (Phase 9.13).

Detects the primary business flow through the Canonical Diagram graph
and yields a primary backbone path for visualization.
"""

from typing import List, Set

from agents.uml_generator.graph_model import DirectedGraph
from config.logging import get_logger

logger = get_logger("agents.uml_generator.business_flow_layout")


class BusinessFlowAnalyzer:
    """Analyzes a directed graph to find the dominant business path."""

    @classmethod
    def compute_primary_path(cls, graph: DirectedGraph) -> List[str]:
        """Compute the longest path from entry nodes to exit nodes."""
        entry_nodes = []
        
        # Priority 1: Actors
        for n in graph.nodes.values():
            if n.node_type == "actor":
                entry_nodes.append(n.id)
                
        # Priority 2: Nodes with no incoming edges (excluding packages)
        if not entry_nodes:
            for n in graph.nodes.values():
                if len(graph.get_in_edges(n.id)) == 0 and n.node_type != "package":
                    entry_nodes.append(n.id)
                    
        if not entry_nodes:
            # Fallback to first capability
            caps = [n.id for n in graph.nodes.values() if n.node_type == "capability"]
            if caps:
                entry_nodes.append(caps[0])
            else:
                return []
            
        best_path: List[str] = []
        
        def dfs(current: str, path: List[str], visited: Set[str]) -> None:
            nonlocal best_path
            
            current_node = graph.get_node(current)
            if current_node and current_node.node_type == "database":
                # Do not extend path into DBs for the backbone
                return
                
            if len(path) > len(best_path):
                best_path = list(path)
                
            for edge in graph.get_out_edges(current):
                if edge.is_backward:
                    continue
                tgt = edge.target_id
                tgt_node = graph.get_node(tgt)
                
                if not tgt_node or tgt_node.node_type == "package":
                    continue
                    
                if tgt not in visited:
                    visited.add(tgt)
                    dfs(tgt, path + [tgt], visited)
                    visited.remove(tgt)

        for entry in entry_nodes:
            dfs(entry, [entry], {entry})
            
        logger.info(f"Identified primary business backbone: {best_path}")
        return best_path
