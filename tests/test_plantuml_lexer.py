"""Unit and regression tests for PlantUML structural lexer/parser and ArchitectureValidator."""

from agents.uml_generator.uml_parser import PlantUMLParser
from agents.uml_generator.validators import ArchitectureValidator


def test_directional_arrows_parsing():
    """Test parsing relationship arrows with direction modifiers (-right->, -down->, .[left].>)."""
    puml = """@startuml
component "Order Service" as cap_order
component "Payment Service" as cap_payment
database "Order DB" as db_order

cap_order -right-> cap_payment : Process Payment
cap_order -down-> db_order : Persist Order
cap_payment .[left].> cap_order : Payment Callback
@enduml"""

    diagram = PlantUMLParser.parse(puml)
    assert len(diagram.relationships) == 3

    rel_sources = [r.source for r in diagram.relationships]
    rel_targets = [r.target for r in diagram.relationships]

    assert rel_sources == ["cap_order", "cap_order", "cap_payment"]
    assert rel_targets == ["cap_payment", "db_order", "cap_order"]

    # Ensure direction tokens (right, down, left) are NOT part of the node aliases
    for node in diagram.nodes:
        assert node.alias not in ("right", "down", "left")
        assert node.display_name not in ("right", "down", "left")


def test_non_relationship_directive_filtering():
    """Test that non-relationship directives (title, package, skinparam, direction, notes) are ignored."""
    puml = """@startuml "SEBI Compliance System"
title Compliance Monitoring Solution - Core Capabilities
left to right direction
skinparam defaultFontName Arial
skinparam componentStyle uml2

package "Compliance Core Package" {
  component "Circular Ingestion" as cap_ingest
  component "Gap Analysis" as cap_gap
}

note right of cap_ingest
  Ingests SEBI circular documents
end note

cap_ingest -right-> cap_gap : Forwards Circular
@enduml"""

    diagram = PlantUMLParser.parse(puml)
    
    # Verify nodes
    node_aliases = {n.alias for n in diagram.nodes}
    assert "cap_ingest" in node_aliases
    assert "cap_gap" in node_aliases

    # Assert title, skinparam, direction, note are NOT added as nodes or aliases
    for invalid_alias in ["title", "Compliance Monitoring Solution", "skinparam", "left to right direction", "note"]:
        assert invalid_alias not in node_aliases

    # Verify relationship
    assert len(diagram.relationships) == 1
    rel = diagram.relationships[0]
    assert rel.source == "cap_ingest"
    assert rel.target == "cap_gap"


def test_architecture_validation_no_false_positives():
    """Test ArchitectureValidator on complex component diagram with directives and directional arrows."""
    puml = """@startuml "Compliance System"
title SEBI Compliance Monitoring
top to bottom direction
skinparam monochrome true

actor "User" as actor_user
package "Core Domain" {
  component "Ingestion Service" as cap_ingest
  component "Analysis Service" as cap_analysis
}
database "Compliance DB" as db_store

actor_user -right-> cap_ingest : Submit
cap_ingest -down-> db_store : Save
cap_ingest -right-> cap_analysis : Process
cap_analysis -down-> db_store : Update
@enduml"""

    plan = """{
      "actors": ["User"],
      "major_components": ["Ingestion Service", "Analysis Service"],
      "major_data_stores": ["Compliance DB"]
    }"""

    validator = ArchitectureValidator()
    result = validator.validate("component", plan, puml)

    assert result["passed"] is True
    assert result["score"] == 100
    assert len(result["errors"]) == 0
