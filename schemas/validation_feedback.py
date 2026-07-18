"""Structured Validation Feedback Models.

Provides rich diagnostic models across Grammar, Architecture, Business Flow,
Layout, Readability, and Traceability categories for UML diagram validation and repair.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DiagnosticCategory(str, Enum):
    """Categories of UML validation diagnostics."""
    GRAMMAR = "Grammar"
    ARCHITECTURE = "Architecture"
    BUSINESS_FLOW = "Business Flow"
    LAYOUT = "Layout"
    READABILITY = "Readability"
    TRACEABILITY = "Traceability"


class ValidationDiagnostic(BaseModel):
    """Individual structured diagnostic item."""
    category: DiagnosticCategory = Field(..., description="Category of diagnostic")
    code: str = Field(..., description="Diagnostic error code (e.g. UNKNOWN_KEYWORD, DISCONNECTED_COMPONENT, HALLUCINATED_COMPONENT)")
    message: str = Field(..., description="Human-readable diagnostic message")
    target_element: Optional[str] = Field(None, description="Affected element name or alias if applicable")
    suggested_fix: Optional[str] = Field(None, description="Actionable recommendation for repair")

    def to_dict(self) -> Dict[str, Any]:
        """Convert diagnostic to dictionary representation."""
        return self.model_dump()


class StructuredValidationFeedback(BaseModel):
    """Container aggregating structured diagnostics across validation layers."""
    validator: str = Field("Validation Pipeline", description="Name of the validator or pipeline")
    passed: bool = Field(True, description="Whether the diagram passed validation")
    score: int = Field(100, description="Overall validation score (0-100)")
    diagnostics: List[ValidationDiagnostic] = Field(default_factory=list, description="Categorized diagnostic list")
    errors: List[str] = Field(default_factory=list, description="Legacy string error list for backward compatibility")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")

    def get_diagnostics_by_category(self, category: DiagnosticCategory) -> List[ValidationDiagnostic]:
        """Filter diagnostics by category."""
        return [d for d in self.diagnostics if d.category == category]
