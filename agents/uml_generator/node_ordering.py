"""Node Ordering (Workstream 4).

Validates and finalizes the left-to-right ordering of nodes within each layer,
ensuring packages are kept together and topological constraints are respected.
"""

from __future__ import annotations

from typing import List

from agents.uml_generator.graph_model import DirectedGraph
from config.logging import get_logger

logger = get_logger("agents.uml_generator.node_ordering")


class NodeOrderer:
    """Finalizes left-to-right ordering within layers."""
    
    @classmethod
    def finalize_ordering(cls, graph: DirectedGraph) -> None:
        """Ensure packages are clustered together horizontally."""
        layer_2 = graph.get_layer_nodes(2)
        
        packages = {}
        standalone = []
        for n in layer_2:
            if n.node_type == "package":
                continue 
            
            if n.parent_package_id:
                if n.parent_package_id not in packages:
                    packages[n.parent_package_id] = []
                packages[n.parent_package_id].append(n)
            else:
                standalone.append(n)

        package_orders = {}
        for pkg_id, caps in packages.items():
            package_orders[pkg_id] = sum(c.order for c in caps) / len(caps)

        sorted_packages = sorted(package_orders.keys(), key=lambda pid: package_orders[pid])
        
        elements_with_order = []
        for pkg_id in sorted_packages:
            elements_with_order.append((package_orders[pkg_id], packages[pkg_id]))
        for cap in standalone:
            elements_with_order.append((cap.order, [cap]))
            
        elements_with_order.sort(key=lambda x: x[0])
        
        final_index = 0
        for _, group in elements_with_order:
            for cap in group:
                cap.order = final_index
                final_index += 1
                
        # Package nodes take the order of their first capability to align properly
        for n in layer_2:
            if n.node_type == "package":
                if n.id in packages and packages[n.id]:
                    n.order = packages[n.id][0].order
