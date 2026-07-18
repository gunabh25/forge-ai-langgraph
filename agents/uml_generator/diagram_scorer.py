"""Enterprise Diagram Scorer.

Calculates quantitative 0-100 scores across 9 quality dimensions:
1. Grammar
2. Architecture
3. Business Flow
4. Layout
5. Readability
6. Whitespace
7. Crossings
8. Package Cohesion
9. Relationship Clarity

Determines production readiness based on threshold (overall_score >= 90.0).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from schemas.canonical_diagram import (
    BaseCanonicalDiagram,
    ComponentDiagramCanonical,
    SequenceDiagramCanonical,
)
from schemas.diagram_score import DiagramScoreCard, PRODUCTION_READINESS_THRESHOLD
from agents.uml_generator.layout_engine import DeterministicLayoutEngine, EngineLayoutResult
from config.logging import get_logger

logger = get_logger("agents.uml_generator.diagram_scorer")


class EnterpriseDiagramScorer:
    """Quantitative scoring engine for UML diagrams."""

    # Metric Weighting Profile (sum = 1.0)
    WEIGHTS = {
        "grammar": 0.15,
        "architecture": 0.15,
        "business_flow": 0.15,
        "layout": 0.10,
        "readability": 0.10,
        "whitespace": 0.10,
        "crossings": 0.10,
        "package_cohesion": 0.075,
        "relationship_clarity": 0.075,
    }

    @classmethod
    def evaluate(
        cls,
        diagram_type: str,
        plantuml_content: str,
        canonical_diagram: Optional[BaseCanonicalDiagram] = None,
        grammar_res: Optional[Dict[str, Any]] = None,
        arch_res: Optional[Dict[str, Any]] = None,
        flow_res: Optional[Dict[str, Any]] = None,
        layout_result: Optional[EngineLayoutResult] = None,
    ) -> DiagramScoreCard:
        """Calculate complete 9-metric score card for a diagram.
        
        Args:
            diagram_type: Type of diagram ('component' or 'sequence').
            plantuml_content: Raw or fixed PlantUML syntax text.
            canonical_diagram: Parsed BaseCanonicalDiagram model instance.
            grammar_res: Result dict from GrammarValidator.
            arch_res: Result dict from ArchitectureValidator.
            flow_res: Result dict from BusinessFlowValidator.
            layout_result: Result from DeterministicLayoutEngine layout computation.

        Returns:
            DiagramScoreCard instance.
        """
        # 1. Grammar Score (15%)
        grammar_score = cls._score_grammar(grammar_res, plantuml_content)

        # 2. Architecture Score (15%)
        architecture_score = cls._score_architecture(arch_res, canonical_diagram)

        # 3. Business Flow Score (15%)
        business_flow_score = cls._score_business_flow(flow_res)

        # 4. Compute or use Layout Result if canonical diagram available
        if canonical_diagram and isinstance(canonical_diagram, ComponentDiagramCanonical) and not layout_result:
            try:
                layout_result = DeterministicLayoutEngine.compute_component_layout(canonical_diagram)
            except Exception as e:
                logger.warning("Layout computation failed during scoring: %s", e)

        # 4. Layout Score (10%)
        layout_score = cls._score_layout(layout_result, plantuml_content)

        # 5. Readability Score (10%)
        readability_score = cls._score_readability(plantuml_content, canonical_diagram)

        # 6. Whitespace Score (10%)
        whitespace_score = cls._score_whitespace(layout_result, canonical_diagram)

        # 7. Crossings Score (10%)
        crossings_score = cls._score_crossings(layout_result, canonical_diagram)

        # 8. Package Cohesion Score (7.5%)
        package_cohesion_score = cls._score_package_cohesion(canonical_diagram)

        # 9. Relationship Clarity Score (7.5%)
        relationship_clarity_score = cls._score_relationship_clarity(canonical_diagram, plantuml_content)

        # Weighted Aggregate Overall Score
        overall_score = (
            grammar_score * cls.WEIGHTS["grammar"]
            + architecture_score * cls.WEIGHTS["architecture"]
            + business_flow_score * cls.WEIGHTS["business_flow"]
            + layout_score * cls.WEIGHTS["layout"]
            + readability_score * cls.WEIGHTS["readability"]
            + whitespace_score * cls.WEIGHTS["whitespace"]
            + crossings_score * cls.WEIGHTS["crossings"]
            + package_cohesion_score * cls.WEIGHTS["package_cohesion"]
            + relationship_clarity_score * cls.WEIGHTS["relationship_clarity"]
        )

        overall_score = round(max(0.0, min(100.0, overall_score)), 1)
        is_production_ready = overall_score >= PRODUCTION_READINESS_THRESHOLD

        breakdown = {
            "grammar": round(grammar_score, 1),
            "architecture": round(architecture_score, 1),
            "business_flow": round(business_flow_score, 1),
            "layout": round(layout_score, 1),
            "readability": round(readability_score, 1),
            "whitespace": round(whitespace_score, 1),
            "crossings": round(crossings_score, 1),
            "package_cohesion": round(package_cohesion_score, 1),
            "relationship_clarity": round(relationship_clarity_score, 1),
        }

        return DiagramScoreCard(
            grammar_score=round(grammar_score, 1),
            architecture_score=round(architecture_score, 1),
            business_flow_score=round(business_flow_score, 1),
            layout_score=round(layout_score, 1),
            readability_score=round(readability_score, 1),
            whitespace_score=round(whitespace_score, 1),
            crossings_score=round(crossings_score, 1),
            package_cohesion_score=round(package_cohesion_score, 1),
            relationship_clarity_score=round(relationship_clarity_score, 1),
            overall_score=overall_score,
            is_production_ready=is_production_ready,
            breakdown_summary=breakdown,
        )

    # -----------------------------------------------------------------------
    # Individual Metric Evaluators
    # -----------------------------------------------------------------------

    @classmethod
    def _score_grammar(cls, grammar_res: Optional[Dict[str, Any]], content: str) -> float:
        """Evaluate syntax validity and keyword correctness."""
        if not grammar_res:
            return 100.0 if "@startuml" in content and "@enduml" in content else 50.0

        if not grammar_res.get("passed", True):
            res_score = float(grammar_res.get("score", 0.0))
            errors = grammar_res.get("errors", [])
            penalty = len(errors) * 25.0
            return max(0.0, min(res_score, 100.0 - penalty))

        return float(grammar_res.get("score", 100.0))

    @classmethod
    def _score_architecture(cls, arch_res: Optional[Dict[str, Any]], canonical: Optional[BaseCanonicalDiagram]) -> float:
        """Evaluate architectural component compliance."""
        if arch_res:
            if not arch_res.get("passed", True):
                res_score = float(arch_res.get("score", 0.0))
                errors = arch_res.get("errors", [])
                penalty = len(errors) * 20.0
                return max(0.0, min(res_score, 100.0 - penalty))
            return float(arch_res.get("score", 100.0))

        if canonical:
            total_elements = len(canonical.all_element_ids())
            return 100.0 if total_elements > 0 else 50.0

        return 100.0

    @classmethod
    def _score_business_flow(cls, flow_res: Optional[Dict[str, Any]]) -> float:
        """Evaluate business interaction flow alignment."""
        if not flow_res:
            return 100.0

        if not flow_res.get("passed", True):
            res_score = float(flow_res.get("score", 0.0))
            errors = flow_res.get("errors", [])
            penalty = len(errors) * 20.0
            return max(0.0, min(res_score, 100.0 - penalty))

        return float(flow_res.get("score", 100.0))

    @classmethod
    def _score_layout(cls, layout_res: Optional[EngineLayoutResult], content: str) -> float:
        """Evaluate spatial placement layer and layout direction directive quality."""
        score = 100.0
        if layout_res:
            if not layout_res.direction_directive:
                score -= 15.0
            if not layout_res.layers.element_layer_map:
                score -= 20.0
        else:
            # Check for layout directives in PlantUML content
            if "top to bottom direction" not in content and "left to right direction" not in content:
                score -= 10.0

        return max(0.0, score)

    @classmethod
    def _score_readability(cls, content: str, canonical: Optional[BaseCanonicalDiagram]) -> float:
        """Evaluate alias usage, diagram title presence, and text complexity."""
        score = 100.0
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        # Check for title
        has_title = any(line.startswith("title ") or line.startswith("header ") for line in lines)
        if not has_title and canonical and canonical.metadata.title:
            score -= 10.0

        # Check line length / complexity
        long_lines = [line for line in lines if len(line) > 120]
        if long_lines:
            score -= min(20.0, len(long_lines) * 5.0)

        return max(0.0, score)

    @classmethod
    def _score_whitespace(cls, layout_res: Optional[EngineLayoutResult], canonical: Optional[BaseCanonicalDiagram]) -> float:
        """Evaluate spatial density ratio and overcrowding across grid layers."""
        if not layout_res or not layout_res.layers:
            return 100.0

        score = 100.0
        layer_counts = [
            len(layout_res.layers.layer_0_actors),
            len(layout_res.layers.layer_1_ext_ingest),
            len(layout_res.layers.layer_2_packages) + len(layout_res.layers.layer_2_capabilities),
            len(layout_res.layers.layer_3_ext_downstream),
            len(layout_res.layers.layer_4_databases),
        ]

        for count in layer_counts:
            if count > 6:  # Overcrowded layer penalty
                score -= (count - 6) * 10.0

        return max(0.0, score)

    @classmethod
    def _score_crossings(cls, layout_res: Optional[EngineLayoutResult], canonical: Optional[BaseCanonicalDiagram]) -> float:
        """Evaluate layer index distance spanning to minimize line crossings."""
        if not canonical or not layout_res:
            return 100.0

        score = 100.0
        layer_map = layout_res.layers.element_layer_map

        for rel in canonical.relationships:
            src_layer = layer_map.get(rel.source_id)
            tgt_layer = layer_map.get(rel.target_id)
            if src_layer is not None and tgt_layer is not None:
                span = abs(tgt_layer - src_layer)
                if span > 2:  # Long span across multiple layers increases crossing probability
                    score -= (span - 2) * 5.0

        return max(0.0, score)

    @classmethod
    def _score_package_cohesion(cls, canonical: Optional[BaseCanonicalDiagram]) -> float:
        """Evaluate capability grouping ratio inside business packages."""
        if not isinstance(canonical, ComponentDiagramCanonical):
            return 100.0

        total_capabilities = len(canonical.business_capabilities)
        if total_capabilities == 0:
            return 100.0

        packaged_capability_ids = set()
        for pkg in canonical.business_packages:
            packaged_capability_ids.update(pkg.capability_ids)

        cohesion_ratio = len(packaged_capability_ids) / float(total_capabilities)
        return min(100.0, cohesion_ratio * 100.0)

    @classmethod
    def _score_relationship_clarity(cls, canonical: Optional[BaseCanonicalDiagram], content: str) -> float:
        """Evaluate relationship labeling clarity and endpoint specificity."""
        if canonical and canonical.relationships:
            total_rels = len(canonical.relationships)
            labeled_rels = sum(1 for r in canonical.relationships if r.label and r.label.strip())
            clarity_ratio = labeled_rels / float(total_rels)
            return round(clarity_ratio * 100.0, 1)

        # Fallback check in PlantUML syntax text
        rel_lines = [l for l in content.splitlines() if "-->" in l or "->" in l or ".." in l]
        if not rel_lines:
            return 100.0

        labeled_lines = [l for l in rel_lines if ":" in l and l.split(":")[-1].strip()]
        return round((len(labeled_lines) / float(len(rel_lines))) * 100.0, 1)
