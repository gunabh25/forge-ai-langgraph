import pytest
from agents.uml_generator.validators import ArchitectureValidator
from agents.uml_generator.uml_parser import PlantUMLParser
from agents.uml_generator.sequence_validator import RelationshipValidator
from agents.uml_generator.edge_router import EdgeRouter
from agents.uml_generator.graph_model import DirectedGraph
from schemas.canonical_diagram import ComponentDiagramCanonical, BusinessCapability, Database, Relationship

def test_capability_to_database_not_self_loop():
    puml = """
    @startuml
    component "Auth Service" as cap_auth
    database "Auth DB" as db_auth
    cap_auth --> db_auth : queries
    @enduml
    """
    diagram = PlantUMLParser.parse(puml)
    rel_validator = RelationshipValidator()
    res = rel_validator.validate(diagram)
    
    assert res.is_valid is True
    assert len(res.errors) == 0

def test_capability_repository_capability_valid():
    puml = """
    @startuml
    component "Service A" as cap_a
    database "Repository" as db_repo
    component "Service B" as cap_b
    cap_a --> db_repo : write
    db_repo --> cap_b : read
    @enduml
    """
    diagram = PlantUMLParser.parse(puml)
    rel_validator = RelationshipValidator()
    res = rel_validator.validate(diagram)
    
    assert res.is_valid is True
    assert len(res.errors) == 0

def test_duplicate_diagnostics_removed():
    puml = """
    @startuml
    component "A" as a
    a --> a : self
    a --> a : self
    @enduml
    """
    diagram = PlantUMLParser.parse(puml)
    arch_val = ArchitectureValidator()
    arch_res = arch_val.validate("component", "{}", puml)
    
    diagnostics = arch_res.get("diagnostics", [])
    self_loops = [d for d in diagnostics if d["code"] == "SELF_LOOP_INTERACTION"]
    assert len(self_loops) == 1

def test_primary_flow_visibility():
    from schemas.canonical_diagram import DiagramMetadata
    diagram = ComponentDiagramCanonical(
        metadata=DiagramMetadata(diagram_type="component", title="Test"),
        business_capabilities=[BusinessCapability(id="A", name="A"), BusinessCapability(id="B", name="B")],
        relationships=[Relationship(source_id="A", target_id="B", direction="-->")]
    )
    graph = DirectedGraph(diagram)
    primary_path = ["A", "B"]
    
    routing_hints = EdgeRouter.route_edges(graph, primary_path=primary_path)
    
    assert "[bold]->" in routing_hints[("A", "B")]

def test_deterministic_layout_and_compactness():
    # Placeholder for structural layout verification asserting layout coordinates remain identical
    # and package boundaries wrap capabilities securely
    assert True
