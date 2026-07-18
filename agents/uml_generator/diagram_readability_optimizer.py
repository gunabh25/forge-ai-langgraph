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

logger = get_logger("agents.uml_generator.diagram_readability_optimizer")

LABEL_WRAP_THRESHOLD = 30
IDEAL_DENSITY_MIN = 0.55
IDEAL_DENSITY_MAX = 0.75


class DiagramReadabilityOptimizer:
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
    def optimize(cls, diagram: ComponentDiagramCanonical) -> Dict[str, Any]:
        """Run full readability optimization pass. Returns readability metrics."""
        density = cls.compute_visual_density(diagram)
        imbalance_warnings = cls.detect_package_imbalance(diagram)

        density_status = "optimal"
        if density < IDEAL_DENSITY_MIN:
            density_status = "sparse"
        elif density > IDEAL_DENSITY_MAX:
            density_status = "dense"

        metrics = {
            "visual_density": density,
            "density_status": density_status,
            "package_imbalance_warnings": imbalance_warnings,
        }

        if imbalance_warnings:
            for w in imbalance_warnings:
                logger.warning("Readability: %s", w)

        return metrics
