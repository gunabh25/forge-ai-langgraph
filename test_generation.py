import asyncio
from schemas.canonical_diagram import (
    ComponentDiagramCanonical,
    DiagramMetadata,
    Actor,
    BusinessPackage,
    BusinessCapability,
    Database,
    ExternalSystem,
    Relationship
)
from agents.uml_generator.layout_planner import LayoutPlanner
from agents.uml_generator.plantuml_builder import ComponentPlantUMLBuilder

diagram = ComponentDiagramCanonical(
    metadata=DiagramMetadata(diagram_type="component", title="Test Arch"),
    actors=[Actor(id="actor_1", name="User")],
    external_systems=[ExternalSystem(id="ext_sys_1", name="Legacy System")],
    business_packages=[BusinessPackage(id="pkg_core", name="Core", capability_ids=["cap_1"])],
    business_capabilities=[BusinessCapability(id="cap_1", name="Service")],
    databases=[Database(id="db_1", name="Main DB")],
    relationships=[
        Relationship(source_id="actor_1", target_id="cap_1", direction="-->", label="Uses"),
        Relationship(source_id="cap_1", target_id="db_1", direction="-->", label="Saves to"),
        Relationship(source_id="cap_1", target_id="ext_sys_1", direction="-->", label="Notifies"),
    ]
)

layout = LayoutPlanner.plan_component_layout(diagram)
builder = ComponentPlantUMLBuilder()
puml = builder.build(diagram, layout)
print(puml)
