"""Unit tests for EnterpriseDiagramScorer and DiagramScoreCard."""

from schemas.canonical_diagram import (
    Actor,
    BusinessCapability,
    Database,
    BusinessPackage,
    Relationship,
    DiagramMetadata,
    ComponentDiagramCanonical,
)
from schemas.diagram_score import DiagramScoreCard, PRODUCTION_READINESS_THRESHOLD
from agents.uml_generator.diagram_scorer import EnterpriseDiagramScorer
from agents.uml_generator.layout_engine import DeterministicLayoutEngine


def test_diagram_score_card_model():
    """Test DiagramScoreCard instantiation and threshold check."""
    score_card = DiagramScoreCard(
        grammar_score=95.0,
        architecture_score=90.0,
        business_flow_score=92.0,
        layout_score=95.0,
        readability_score=90.0,
        whitespace_score=95.0,
        crossings_score=90.0,
        package_cohesion_score=100.0,
        relationship_clarity_score=100.0,
        overall_score=93.5,
        is_production_ready=True,
    )
    assert score_card.overall_score == 93.5
    assert score_card.is_production_ready is True
    assert score_card.overall_score >= PRODUCTION_READINESS_THRESHOLD


def test_enterprise_diagram_scorer_high_quality():
    """Test EnterpriseDiagramScorer on a well-structured canonical diagram."""
    diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Order Management System"),
        actors=[Actor(id="actor_user", name="User")],
        business_capabilities=[
            BusinessCapability(id="cap_order", name="Order Service"),
            BusinessCapability(id="cap_payment", name="Payment Service"),
        ],
        business_packages=[
            BusinessPackage(id="pkg_core", name="Core Package", capability_ids=["cap_order", "cap_payment"])
        ],
        databases=[Database(id="db_order", name="Order Database")],
        relationships=[
            Relationship(source_id="actor_user", target_id="cap_order", direction="-->", label="Submit Order"),
            Relationship(source_id="cap_order", target_id="cap_payment", direction="-->", label="Process Payment"),
            Relationship(source_id="cap_order", target_id="db_order", direction="-->", label="Save Order"),
        ],
    )

    plantuml_content = """@startuml "Order Management System"
top to bottom direction
actor "User" as actor_user
package "Core Package" as pkg_core {
  component "Order Service" as cap_order
  component "Payment Service" as cap_payment
}
database "Order Database" as db_order

actor_user --> cap_order : Submit Order
cap_order --> cap_payment : Process Payment
cap_order --> db_order : Save Order
@enduml"""

    grammar_res = {"passed": True, "score": 100, "errors": []}
    arch_res = {"passed": True, "score": 100, "errors": []}
    flow_res = {"passed": True, "score": 100, "errors": []}

    layout_res = DeterministicLayoutEngine.compute_component_layout(diagram)

    score_card = EnterpriseDiagramScorer.evaluate(
        diagram_type="component",
        plantuml_content=plantuml_content,
        canonical_diagram=diagram,
        grammar_res=grammar_res,
        arch_res=arch_res,
        flow_res=flow_res,
        layout_result=layout_res,
    )

    assert score_card.overall_score >= 90.0
    assert score_card.is_production_ready is True
    assert score_card.package_cohesion_score == 100.0
    assert score_card.relationship_clarity_score == 100.0


def test_enterprise_diagram_scorer_low_quality():
    """Test EnterpriseDiagramScorer on a flawed diagram with errors."""
    plantuml_content = "invalid plantuml content without start/end tags"

    grammar_res = {"passed": False, "score": 0, "errors": ["Syntax error: unknown keyword"]}
    arch_res = {"passed": False, "score": 40, "errors": ["Hallucinated component found"]}

    score_card = EnterpriseDiagramScorer.evaluate(
        diagram_type="component",
        plantuml_content=plantuml_content,
        grammar_res=grammar_res,
        arch_res=arch_res,
    )

    assert score_card.overall_score < 90.0
    assert score_card.is_production_ready is False
