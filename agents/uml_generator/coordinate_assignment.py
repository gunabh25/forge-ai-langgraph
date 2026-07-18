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
            
        # Assign basic X coordinates based on relative ordering within layer
        for i in range(5):
            layer_nodes = graph.get_layer_nodes(i)
            x = 0.0
            for node in layer_nodes:
                if node.node_type == "package":
                    continue
                    
                # Enforce Actor separation (Phase 9.8)
                if node.node_type == "actor":
                    node.x = 0.0
                    x = max(x, 10.0)  # Reserve left column
                    continue
                    
                # Enforce External System separation
                if node.node_type == "external_system":
                    if i == 1: # Ingest / Producer
                        node.x = x
                        x += node.width + 5.0 # Extra padding
                    else: # Downstream / Consumer
                        # Push far right
                        node.x = max(x, 50.0)
                        x = node.x + node.width + 5.0
                    continue

                if x < 10.0 and i > 0:
                    x = 10.0 # Force core components into middle column

                node.x = x
                x += node.width + 0.5

        # Database Alignment (Workstream 8): Center databases under consuming capability
        db_nodes = [n for n in graph.nodes.values() if n.node_type == "database"]
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
                    db.x = sum_x / valid_srcs
                
        # Sort layer 4 by X coordinate to ensure PlantUML serializes them correctly
        layer_4 = graph.get_layer_nodes(4)
        layer_4.sort(key=lambda n: n.x)
        for order, db in enumerate(layer_4):
            db.order = order
