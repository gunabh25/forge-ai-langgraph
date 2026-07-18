"""Diagram Readability Optimizer.

Deterministic post-layout readability pass that optimizes:
1. Relationship label wrapping (>30 chars → line-break)
2. Visual density score (elements / canvas area estimate)
3. Package balance warnings (7 vs 1 component imbalance)

This module is presentation-only. It does NOT modify canonical diagram models,
stable IDs, capabilities, relationships, or architecture reasoning.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from schemas.canonical_diagram import ComponentDiagramCanonical
from config.logging import get_logger

logger = get_logger("agents.uml_generator.readability_optimizer")

LABEL_WRAP_THRESHOLD = 30
IDEAL_DENSITY_MIN = 0.55
IDEAL_DENSITY_MAX = 0.75


class ReadabilityOptimizer:
    """Post-layout readability optimizer for PlantUML component diagrams."""

    @classmethod
    def wrap_label(cls, label: str, max_width: int = LABEL_WRAP_THRESHOLD) -> str:
        """Wrap a label using \\n if it exceeds max_width characters."""
        if not label or len(label) <= max_width:
            return label

        words = label.split()
        lines: List[str] = []
        current_line = ""

        for word in words:
            if current_line and len(current_line) + 1 + len(word) > max_width:
                lines.append(current_line)
                current_line = word
            else:
                current_line = f"{current_line} {word}".strip()

        if current_line:
            lines.append(current_line)

        return "\\n".join(lines)

    @classmethod
    def compute_visual_density(cls, diagram: ComponentDiagramCanonical) -> float:
        """Compute visual density score: elements / estimated canvas cells.
        
        Ideal range: 0.55–0.75.
        """
        total_elements = len(diagram.all_elements())
        num_packages = len(diagram.business_packages)
        # Estimate canvas as grid: max(3, sqrt(elements) * 2) rows × cols
        import math
        grid_size = max(3, int(math.sqrt(total_elements) * 2))
        canvas_cells = grid_size * grid_size
        density = total_elements / float(canvas_cells) if canvas_cells > 0 else 0.0
        return round(density, 3)

    @classmethod
    def detect_package_imbalance(cls, diagram: ComponentDiagramCanonical) -> List[str]:
        """Detect packages with significantly unbalanced component counts."""
        warnings: List[str] = []
        if len(diagram.business_packages) < 2:
            return warnings

        sizes = [(pkg.name, len(pkg.capability_ids)) for pkg in diagram.business_packages]
        max_size = max(s for _, s in sizes)
        min_size = min(s for _, s in sizes)

        if max_size > 0 and min_size > 0 and max_size / min_size > 5:
            largest = [name for name, s in sizes if s == max_size]
            smallest = [name for name, s in sizes if s == min_size]
            warnings.append(
                f"Package imbalance detected: {largest[0]} has {max_size} capabilities "
                f"while {smallest[0]} has {min_size}. Consider rebalancing for visual symmetry."
            )

        return warnings

    @classmethod
    def compute_adaptive_spacing(cls, diagram: ComponentDiagramCanonical) -> tuple[int, int]:
        """Compute (ranksep, nodesep) dynamically based on diagram size and labels."""
        total_elements = len(diagram.all_elements())
        num_packages = len(diagram.business_packages)
        
        labels = [cap.name for cap in diagram.business_capabilities]
        avg_label_len = sum(len(l) for l in labels) / max(1, len(labels))
        
        ranksep = min(250, max(120, 100 + total_elements + (num_packages * 10)))
        nodesep = min(180, max(90, int(avg_label_len * 3.5)))
        
        # pyrefly: ignore [unnecessary-type-conversion]
        return int(ranksep), int(nodesep)

    @classmethod
    def infer_render_time_packages(cls, diagram: ComponentDiagramCanonical) -> List[Dict[str, Any]]:
        """Infer visual packages if none exist by clustering strongly connected capabilities."""
        if diagram.business_packages:
            return []
            
        from collections import defaultdict
        adj = defaultdict(set)
        for rel in diagram.relationships:
            if rel.source_id.startswith("cap_") and rel.target_id.startswith("cap_"):
                adj[rel.source_id].add(rel.target_id)
                adj[rel.target_id].add(rel.source_id)
                
        visited = set()
        clusters = []
        
        for cap in diagram.business_capabilities:
            if cap.id not in visited:
                cluster_caps = set()
                queue = [cap.id]
                while queue:
                    curr = queue.pop(0)
                    if curr not in visited:
                        visited.add(curr)
                        cluster_caps.add(curr)
                        for neighbor in adj[curr]:
                            if neighbor not in visited:
                                queue.append(neighbor)
                if cluster_caps:
                    clusters.append(cluster_caps)
                    
        inferred = []
        for i, cluster_caps in enumerate(clusters):
            names = [c.name for c in diagram.business_capabilities if c.id in cluster_caps]
            if len(names) > 1:
                pkg_name = f"{names[0]} Domain"
            else:
                pkg_name = f"{names[0]} System"
                
            inferred.append({
                "id": f"pkg_inferred_{i}",
                "name": pkg_name,
                "capability_ids": list(cluster_caps)
            })
            
        return inferred

    @classmethod
    def compute_business_flow_readability(cls, diagram: ComponentDiagramCanonical, graph: Optional[Any] = None) -> float:
        """Compute visual readability metric (0-100) based on Phase 9.13 requirements."""
        if not graph:
            return 80.0
            
        score = 100.0
        
        # Check Entry Visibility
        actors = [n for n in graph.nodes.values() if n.node_type == "actor"]
        if actors:
            if not all(a.layer == 0 for a in actors):
                score -= 10.0
                
        # Check Database Placement
        dbs = [n for n in graph.nodes.values() if n.node_type == "database"]
        for db in dbs:
            # Databases shouldn't be at X=20 (backbone center)
            if abs(db.x - 20.0) < 1.0:
                score -= 5.0
                
        # Check Primary Flow Continuity
        from agents.uml_generator.business_flow_layout import BusinessFlowAnalyzer
        primary_path = BusinessFlowAnalyzer.compute_primary_path(graph)
        
        continuity_broken = False
        for i in range(len(primary_path) - 1):
            src = graph.get_node(primary_path[i])
            tgt = graph.get_node(primary_path[i+1])
            if src and tgt and abs(tgt.layer - src.layer) > 1:
                continuity_broken = True
                break
                
        if continuity_broken:
            score -= 20.0
            
        return max(0.0, score)

    @classmethod
    def optimize(cls, diagram: ComponentDiagramCanonical, graph: Optional[Any] = None) -> Dict[str, Any]:
        """Run full readability optimization pass. Returns readability metrics."""
        density = cls.compute_visual_density(diagram)
        imbalance_warnings = cls.detect_package_imbalance(diagram)

        density_status = "optimal"
        if density < IDEAL_DENSITY_MIN:
            density_status = "sparse"
        elif density > IDEAL_DENSITY_MAX:
            density_status = "dense"

        ranksep, nodesep = cls.compute_adaptive_spacing(diagram)
        inferred_packages = cls.infer_render_time_packages(diagram)
        
        business_flow_score = cls.compute_business_flow_readability(diagram, graph)

        metrics = {
            "visual_density": density,
            "density_status": density_status,
            "package_imbalance_warnings": imbalance_warnings,
            "adaptive_ranksep": ranksep,
            "adaptive_nodesep": nodesep,
            "inferred_packages": inferred_packages,
            "business_flow_readability": business_flow_score,
        }

        if imbalance_warnings:
            for w in imbalance_warnings:
                logger.warning("Readability: %s", w)

        return metrics
