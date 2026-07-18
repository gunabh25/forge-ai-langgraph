"""Coordinate Assignment (Workstream 5).

Translates discrete layers and node ordering into logical coordinates.
Used for deterministic placement of elements and database alignment.
"""

from __future__ import annotations

from typing import List

from agents.uml_generator.graph_model import DirectedGraph
from config.logging import get_logger

logger = get_logger("agents.uml_generator.coordinate_assignment")


class CoordinateAssigner:
    """Assigns logical X/Y coordinates to nodes."""
    
    @classmethod
    def assign_coordinates(cls, graph: DirectedGraph) -> None:
        """Assign coordinates and perform database alignment (Workstream 8)."""
        # Assign basic Y coordinates (Layer)
        for node in graph.nodes.values():
            node.y = float(node.layer)
            
        max_layer = getattr(graph, "max_layer", 4)
        
        # We define a visual grid layout:
        # X=0: Producer External Systems & Actors
        # X=20: Primary Backbone (Capabilities, UI)
        # X=40: Consumer External Systems
        # X=25: Databases (Offset to not block primary flow)
        
        for i in range(max_layer + 1):
            layer_nodes = sorted(graph.get_layer_nodes(i), key=lambda n: n.id)
            
            # Start backbone at X=20
            secondary_x = 30.0 
            
            for node in layer_nodes:
                if node.node_type == "package":
                    continue
                    
                if node.node_type == "actor":
                    node.x = 20.0  # Center of backbone
                    continue
                    
                if node.node_type == "external_system":
                    in_edges = len(graph.get_in_edges(node.id))
                    out_edges = len(graph.get_out_edges(node.id))
                    if out_edges >= in_edges: # Producer
                        node.x = 0.0
                    else: # Consumer
                        node.x = 40.0
                    continue

                if node.node_type == "database":
                    # Initial assignment, will be re-centered below
                    node.x = 25.0
                    continue
                
                # Capabilities
                # Check if this is the first capability in this layer
                caps_in_layer = [n for n in layer_nodes if n.node_type == "capability"]
                if caps_in_layer and node == caps_in_layer[0]:
                    node.x = 20.0
                else:
                    node.x = secondary_x
                    secondary_x += node.width + 5.0

        # Database Alignment (Workstream 8): Place databases beneath and slightly offset
        db_nodes = sorted([n for n in graph.nodes.values() if n.node_type == "database"], key=lambda n: n.id)
        for db in db_nodes:
            in_edges = graph.get_in_edges(db.id)
            if in_edges:
                sum_x = 0.0
                valid_srcs = 0
                for edge in in_edges:
                    src = graph.get_node(edge.source_id)
                    if src:
                        sum_x += src.x
                        valid_srcs += 1
                if valid_srcs > 0:
                    # Offset database slightly to the right to avoid crossing the primary flow
                    db.x = (sum_x / valid_srcs) + 5.0
                
        # Sort layers by X coordinate to ensure PlantUML serializes them correctly, falling back to ID for stability
        for i in range(max_layer + 1):
            layer_n = sorted(graph.get_layer_nodes(i), key=lambda n: (n.x, n.id))
            for order, node in enumerate(layer_n):
                node.order = order
