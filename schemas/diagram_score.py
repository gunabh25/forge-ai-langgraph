"""Enterprise Diagram Score Models.

Defines quantitative 0-100 score cards and production readiness metrics
for generated UML diagrams across 9 structural and visual quality dimensions.
"""

from __future__ import annotations

from typing import Any, Dict
from pydantic import BaseModel, Field


PRODUCTION_READINESS_THRESHOLD = 90.0


class DiagramScoreCard(BaseModel):
    """Quantitative evaluation metrics (0-100) for a UML diagram."""
    grammar_score: float = Field(100.0, ge=0.0, le=100.0, description="Syntax validity & keywords")
    architecture_score: float = Field(100.0, ge=0.0, le=100.0, description="Entity & connectivity compliance")
    business_flow_score: float = Field(100.0, ge=0.0, le=100.0, description="Sequence & interaction logic alignment")
    layout_score: float = Field(100.0, ge=0.0, le=100.0, description="Spatial layer & direction directive quality")
    readability_score: float = Field(100.0, ge=0.0, le=100.0, description="Alias usage & text complexity")
    whitespace_score: float = Field(100.0, ge=0.0, le=100.0, description="Spatial density ratio & overcrowding balance")
    crossings_score: float = Field(100.0, ge=0.0, le=100.0, description="Edge crossing & layer span optimization")
    package_cohesion_score: float = Field(100.0, ge=0.0, le=100.0, description="Business package grouping ratio")
    relationship_clarity_score: float = Field(100.0, ge=0.0, le=100.0, description="Relationship labeling ratio")
    overall_score: float = Field(100.0, ge=0.0, le=100.0, description="Weighted composite diagram score (0-100)")
    is_production_ready: bool = Field(True, description="True if overall_score >= 90.0")
    breakdown_summary: Dict[str, Any] = Field(default_factory=dict, description="Detailed score metric dictionary")

    def to_dict(self) -> Dict[str, Any]:
        """Convert score card to dictionary."""
        return self.model_dump()
