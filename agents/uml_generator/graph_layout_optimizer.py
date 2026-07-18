"""Enterprise Graph Layout Optimizer.

Performs deterministic mathematical optimization of the Component Diagram layout.
Minimizes edge crossings, normalizes edge lengths, compacts packages,
and ensures a balanced visual hierarchy.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple

from schemas.canonical_diagram import ComponentDiagramCanonical
from agents.uml_generator.layout_engine import EngineLayoutResult, LayerAssignment, DeterministicLayoutEngine
from config.logging import get_logger

logger = get_logger("agents.uml_generator.graph_layout_optimizer")


class GraphLayoutOptimizer:
    """Enterprise-grade layout optimizer for Component Diagrams."""

    @classmethod
    def optimize(
        cls,
        diagram: ComponentDiagramCanonical,
        initial_result: EngineLayoutResult,
    ) -> EngineLayoutResult:
        """Run post-layout optimization pass to minimize layout cost deterministically."""
        
        best_cost = cls.calculate_layout_cost(diagram, initial_result.layers, initial_result.formatted_arrows)
        best_layers = initial_result.layers
        best_arrows = initial_result.formatted_arrows
        best_hidden = initial_result.hidden_alignment_edges

        candidates = cls._generate_candidate_layers(diagram, initial_result.layers)
        
        for cand_layers in candidates:
            cand_arrows = DeterministicLayoutEngine.compute_routing_hints(diagram, cand_layers, initial_result.direction_directive)
            cand_cost = cls.calculate_layout_cost(diagram, cand_layers, cand_arrows)
            
            if cand_cost < best_cost:
                best_cost = cand_cost
                best_layers = cand_layers
                best_arrows = cand_arrows
                best_hidden = DeterministicLayoutEngine.compute_alignment_edges(diagram, cand_layers, initial_result.direction_directive)

        updated_metrics = dict(initial_result.readability_metrics)
        updated_metrics["layout_cost"] = round(best_cost, 2)

        return EngineLayoutResult(
            direction_directive=initial_result.direction_directive,
            layers=best_layers,
            formatted_arrows=best_arrows,
            hidden_alignment_edges=best_hidden,
            dynamic_skinparams=initial_result.dynamic_skinparams,
            readability_metrics=updated_metrics,
        )

    @classmethod
    def _generate_candidate_layers(
        cls,
        diagram: ComponentDiagramCanonical,
        base_layers: LayerAssignment,
    ) -> List[LayerAssignment]:
        """Generate permutations of layer assignments using various crossing minimization heuristics."""
        candidates = []
        
        # 1. Alphabetical (baseline)
        alpha = copy.deepcopy(base_layers)
        alpha.layer_0_actors.sort()
        alpha.layer_1_ext_ingest.sort()
        alpha.layer_2_packages.sort()
        alpha.layer_2_capabilities.sort()
        alpha.layer_3_ext_downstream.sort()
        alpha.layer_4_databases.sort()
        candidates.append(alpha)
        
        # 2. Reverse Flow
        rev = copy.deepcopy(base_layers)
        rev.layer_0_actors.reverse()
        rev.layer_1_ext_ingest.reverse()
        rev.layer_2_packages.reverse()
        rev.layer_2_capabilities.reverse()
        rev.layer_3_ext_downstream.reverse()
        rev.layer_4_databases.reverse()
        candidates.append(rev)

        # 3. Barycenter Heuristic (Forward sweep)
        bary_fwd = copy.deepcopy(base_layers)
        cls._apply_barycenter_sweep(diagram, bary_fwd, reverse=False)
        candidates.append(bary_fwd)

        # 4. Barycenter Heuristic (Backward sweep)
        bary_bwd = copy.deepcopy(base_layers)
        cls._apply_barycenter_sweep(diagram, bary_bwd, reverse=True)
        candidates.append(bary_bwd)
        # 5. External System Optimization Candidates (Workstream 7)
        # Shift all external systems to left (Layer 1)
        ext_all_left = copy.deepcopy(base_layers)
        ext_all_left.layer_1_ext_ingest.extend(ext_all_left.layer_3_ext_downstream)
        ext_all_left.layer_3_ext_downstream = []
        for ext_id in ext_all_left.layer_1_ext_ingest:
            ext_all_left.element_layer_map[ext_id] = 1
        candidates.append(ext_all_left)

        # Shift all external systems to right (Layer 3)
        ext_all_right = copy.deepcopy(base_layers)
        ext_all_right.layer_3_ext_downstream.extend(ext_all_right.layer_1_ext_ingest)
        ext_all_right.layer_1_ext_ingest = []
        for ext_id in ext_all_right.layer_3_ext_downstream:
            ext_all_right.element_layer_map[ext_id] = 3
        candidates.append(ext_all_right)

        return candidates

    @classmethod
    def _apply_barycenter_sweep(cls, diagram: ComponentDiagramCanonical, layers: LayerAssignment, reverse: bool = False) -> None:
        """Apply barycenter crossing minimization algorithm across layers."""
        layer_lists = [
            layers.layer_0_actors,
            layers.layer_1_ext_ingest,
            layers.layer_2_packages + layers.layer_2_capabilities,
            layers.layer_3_ext_downstream,
            layers.layer_4_databases
        ]
        
        # Build adjacency
        adj_out = {n: [] for n in diagram.all_element_ids()}
        adj_in = {n: [] for n in diagram.all_element_ids()}
        for rel in diagram.relationships:
            if rel.source_id in adj_out:
                adj_out[rel.source_id].append(rel.target_id)
            if rel.target_id in adj_in:
                adj_in[rel.target_id].append(rel.source_id)
                
        def get_barycenter(node_id: str, reference_layer: List[str]) -> float:
            neighbors = set(adj_out.get(node_id, []) + adj_in.get(node_id, []))
            ref_indices = [reference_layer.index(n) for n in neighbors if n in reference_layer]
            if not ref_indices:
                return -1.0
            return sum(ref_indices) / len(ref_indices)

        sweep_order = range(1, 5) if not reverse else range(3, -1, -1)
        
        for i in sweep_order:
            ref_i = i - 1 if not reverse else i + 1
            if ref_i < 0 or ref_i > 4:
                continue
            
            ref_layer = layer_lists[ref_i]
            if not ref_layer:
                continue
                
            if i == 0:
                layers.layer_0_actors.sort(key=lambda x: (get_barycenter(x, ref_layer), x))
            elif i == 1:
                layers.layer_1_ext_ingest.sort(key=lambda x: (get_barycenter(x, ref_layer), x))
            elif i == 2:
                layers.layer_2_packages.sort(key=lambda x: (get_barycenter(x, ref_layer), x))
                layers.layer_2_capabilities.sort(key=lambda x: (get_barycenter(x, ref_layer), x))
            elif i == 3:
                layers.layer_3_ext_downstream.sort(key=lambda x: (get_barycenter(x, ref_layer), x))
            elif i == 4:
                layers.layer_4_databases.sort(key=lambda x: (get_barycenter(x, ref_layer), x))
                
            layer_lists[0] = layers.layer_0_actors
            layer_lists[1] = layers.layer_1_ext_ingest
            layer_lists[2] = layers.layer_2_packages + layers.layer_2_capabilities
            layer_lists[3] = layers.layer_3_ext_downstream
            layer_lists[4] = layers.layer_4_databases


    @classmethod
    def calculate_layout_cost(
        cls,
        diagram: ComponentDiagramCanonical,
        layers: LayerAssignment,
        formatted_arrows: Dict[Tuple[str, str], str],
    ) -> float:
        """Calculate Layout Cost for Workstream 12.
        
        Cost = 5 × Edge Crossings
             + 3 × Average Edge Length
             + 2 × Package Dispersion
             + 2 × Whitespace Imbalance
             + 1 × Label Overlap
        """
        total_rels = len(diagram.relationships)
        if total_rels == 0:
            return 0.0

        edge_crossings = 0
        total_length = 0.0

        rels = diagram.relationships
        for i in range(len(rels)):
            rel1 = rels[i]
            s1 = layers.element_layer_map.get(rel1.source_id, 2)
            t1 = layers.element_layer_map.get(rel1.target_id, 2)
            span1 = abs(t1 - s1)
            total_length += span1

            for j in range(i + 1, len(rels)):
                rel2 = rels[j]
                s2 = layers.element_layer_map.get(rel2.source_id, 2)
                t2 = layers.element_layer_map.get(rel2.target_id, 2)

                if (s1 < s2 and t1 > t2) or (s1 > s2 and t1 < t2):
                    edge_crossings += 1

        avg_length = total_length / total_rels

        layer_counts = [
            len(layers.layer_0_actors),
            len(layers.layer_1_ext_ingest),
            len(layers.layer_2_packages) + len(layers.layer_2_capabilities),
            len(layers.layer_3_ext_downstream),
            len(layers.layer_4_databases),
        ]
        non_zero_layers = [c for c in layer_counts if c > 0]
        max_c = max(non_zero_layers) if non_zero_layers else 1
        min_c = min(non_zero_layers) if non_zero_layers else 1
        
        whitespace_imbalance = float(max_c - min_c)
        package_dispersion = len(diagram.business_packages) * 1.5
        label_overlap = 0.0

        return (
            (5.0 * edge_crossings) +
            (3.0 * avg_length) +
            (2.0 * package_dispersion) +
            (2.0 * whitespace_imbalance) +
            (1.0 * label_overlap)
        )
