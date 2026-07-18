"""Unit tests for Rich Validation Feedback and Diagnostic Reporting."""

from schemas.validation_feedback import (
    DiagnosticCategory,
    ValidationDiagnostic,
    StructuredValidationFeedback,
)
from agents.uml_generator.validators import (
    GrammarValidator,
    ArchitectureValidator,
    BusinessFlowValidator,
)
from agents.uml_repair.agent import _build_structured_feedback


def test_validation_diagnostic_model():
    """Test ValidationDiagnostic model instantiation and serialization."""
    diag = ValidationDiagnostic(
        category=DiagnosticCategory.TRACEABILITY,
        code="HALLUCINATED_COMPONENT",
        message="Unapproved service 'FakeService' found in diagram",
        target_element="FakeService",
        suggested_fix="Remove 'FakeService' or replace with approved capability"
    )

    assert diag.category == DiagnosticCategory.TRACEABILITY
    assert diag.code == "HALLUCINATED_COMPONENT"
    assert diag.target_element == "FakeService"
    assert "FakeService" in diag.to_dict()["message"]


def test_structured_validation_feedback_aggregation():
    """Test StructuredValidationFeedback container model and category filtering."""
    diag1 = ValidationDiagnostic(
        category=DiagnosticCategory.GRAMMAR,
        code="SYNTAX_ERROR",
        message="Syntax error at line 4"
    )
    diag2 = ValidationDiagnostic(
        category=DiagnosticCategory.ARCHITECTURE,
        code="DISCONNECTED_COMPONENT",
        message="Component 'OrphanService' has no connections",
        target_element="OrphanService"
    )

    fb = StructuredValidationFeedback(
        validator="Test Validator",
        passed=False,
        score=50,
        diagnostics=[diag1, diag2],
        errors=["Syntax error at line 4", "Component 'OrphanService' has no connections"]
    )

    assert not fb.passed
    assert len(fb.diagnostics) == 2
    grammar_diags = fb.get_diagnostics_by_category(DiagnosticCategory.GRAMMAR)
    arch_diags = fb.get_diagnostics_by_category(DiagnosticCategory.ARCHITECTURE)

    assert len(grammar_diags) == 1
    assert grammar_diags[0].code == "SYNTAX_ERROR"
    assert len(arch_diags) == 1
    assert arch_diags[0].target_element == "OrphanService"


def test_repair_agent_structured_feedback_formatting():
    """Test _build_structured_feedback formats category-grouped diagnostics for Repair Agent."""
    allowed = {"orderservice": "Order Service"}

    # Plain text traceability feedback
    fb_text = _build_structured_feedback("Non-traceable participant found: FakeService", allowed)
    assert "Validation Category : Traceability" in fb_text
    assert "Diagnostic Code     : HALLUCINATED_COMPONENT" in fb_text
    assert "Approved Participants" in fb_text

    # JSON structured feedback
    json_feedback = '{"diagnostics": [{"category": "Architecture", "code": "DISCONNECTED_COMPONENT", "message": "Component disconnected", "target_element": "AuthService", "suggested_fix": "Connect component"}]}'
    fb_json = _build_structured_feedback(json_feedback, allowed)
    assert "Validation Category : Architecture" in fb_json
    assert "Diagnostic Code     : DISCONNECTED_COMPONENT" in fb_json
    assert "Target Element    : AuthService" in fb_json
    assert "Required Fix      : Connect component" in fb_json
