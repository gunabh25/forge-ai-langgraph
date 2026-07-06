"""Quality Engine: calculates weighted quality scores and deployment readiness.

This module is completely independent from LangGraph and ForgeState.
It can be used as a standalone library wherever quality scoring is needed.

Future extensibility: new quality dimensions (Performance, Accessibility,
Compliance, Cost Optimization, Maintainability) can be added by updating
the weights configuration only — no changes to this file are required.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple


@dataclass
class QualityResult:
    """Result produced by the QualityEngine after scoring.

    Attributes:
        overall_score: Final weighted score rounded to the nearest integer [0, 100].
        deployment_status: Human-readable status string (e.g. "NEEDS IMPROVEMENT").
        deployment_emoji: Status emoji prefix (🟢 / 🟡 / 🔴).
        quality_report: Full formatted quality report Markdown.
        score_breakdown: Per-dimension scoring detail (score, weight, contribution).
    """

    overall_score: int
    deployment_status: str
    deployment_emoji: str
    quality_report: str
    score_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class QualityEngine:
    """Independent, reusable quality scoring engine.

    Calculates a weighted overall quality score from multiple validation
    dimensions and determines deployment readiness based on configurable
    thresholds.

    Usage::

        engine = QualityEngine(
            weights={"qa": 0.30, "security": 0.40, "review": 0.30},
            thresholds={"ready": 90, "needs_improvement": 75},
        )
        result = engine.calculate({"qa": 87, "security": 92, "review": 84})
        print(result.overall_score)   # 88
        print(result.deployment_status)  # NEEDS IMPROVEMENT
    """

    def __init__(
        self,
        weights: Dict[str, float],
        thresholds: Optional[Dict[str, int]] = None,
    ) -> None:
        """Initialize the QualityEngine.

        Args:
            weights: Mapping of dimension name → weight (must sum to ≈ 1.0).
            thresholds: Optional deployment thresholds. Keys:
                ``ready`` (default 90) and ``needs_improvement`` (default 75).

        Raises:
            ValueError: If weights contain negative values or don't sum to 1.0.
        """
        self._weights = weights
        self._thresholds = thresholds or {"ready": 90, "needs_improvement": 75}
        self._validate_weights()

    def _validate_weights(self) -> None:
        for key, w in self._weights.items():
            if w < 0:
                raise ValueError(
                    f"Quality weight for '{key}' must be non-negative, got {w}"
                )
        total = sum(self._weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Quality weights must sum to 1.0, got {total:.4f}"
            )

    def calculate(self, scores: Dict[str, int]) -> QualityResult:
        """Calculate the overall quality score for the given dimension scores.

        Dimensions present in ``scores`` but absent from ``weights`` are ignored.
        Dimensions in ``weights`` but absent from ``scores`` are also skipped
        (their weight is excluded from the normalization denominator).

        Args:
            scores: Mapping of dimension name → raw score [0, 100].

        Returns:
            QualityResult with overall score, deployment status, and report.
        """
        weighted_sum = 0.0
        active_weight = 0.0
        breakdown: Dict[str, Dict[str, Any]] = {}

        for dimension, weight in self._weights.items():
            if dimension not in scores:
                continue
            raw = max(0, min(100, scores[dimension]))
            contribution = raw * weight
            weighted_sum += contribution
            active_weight += weight
            breakdown[dimension] = {
                "score": raw,
                "weight": weight,
                "weight_pct": f"{weight * 100:.0f}%",
                "contribution": round(contribution, 2),
            }

        # Normalise if not all dimensions were provided
        if active_weight > 0 and abs(active_weight - 1.0) > 0.01:
            weighted_sum = weighted_sum / active_weight

        overall = max(0, min(100, round(weighted_sum)))
        status, emoji = self._determine_status(overall)
        report = self._generate_report(breakdown, overall, status, emoji)

        return QualityResult(
            overall_score=overall,
            deployment_status=status,
            deployment_emoji=emoji,
            quality_report=report,
            score_breakdown=breakdown,
        )

    def _determine_status(self, score: int) -> Tuple[str, str]:
        ready = self._thresholds.get("ready", 90)
        improvement = self._thresholds.get("needs_improvement", 75)

        if score >= ready:
            return "READY FOR DEPLOYMENT", "🟢"
        elif score >= improvement:
            return "NEEDS IMPROVEMENT", "🟡"
        else:
            return "BLOCKED", "🔴"

    def _generate_report(
        self,
        breakdown: Dict[str, Dict[str, Any]],
        overall: int,
        status: str,
        emoji: str,
    ) -> str:
        lines = [
            "# ForgeAI Quality Report",
            "",
            "====================================",
        ]

        for dim, info in breakdown.items():
            label = dim.replace("_", " ").title()
            lines.append(
                f"{label}: {info['score']}/100  |  Weight: {info['weight_pct']}"
            )

        lines += [
            "--------------------------------",
            f"Overall: {overall}/100",
            f"Deployment Status: {emoji} {status}",
            "====================================",
        ]
        return "\n".join(lines)
