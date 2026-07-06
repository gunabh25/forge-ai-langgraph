"""Mermaid Diagram Generator for ForgeAI workflows."""

from core.artifact_manager import ArtifactManager
from core.constants import ArtifactFolders

class DiagramGenerator:
    """Generates Mermaid (.mmd) diagrams for workflow, architecture, and pipeline."""
    
    @staticmethod
    def generate_all():
        """Generates and saves all Mermaid diagrams."""
        artifact_manager = ArtifactManager()
        
        # 1. Workflow Diagram
        workflow_mmd = """graph TD
    User --> EngineeringManager
    EngineeringManager --> RequirementAnalyst
    RequirementAnalyst --> SolutionArchitect
    SolutionArchitect --> BackendEngineer
    BackendEngineer --> AISoftwareEngineer
    AISoftwareEngineer --> QA
    AISoftwareEngineer --> Security
    AISoftwareEngineer --> CodeReviewer
    QA --> ValidationSummary
    Security --> ValidationSummary
    CodeReviewer --> ValidationSummary
    ValidationSummary --> QualityGate
    QualityGate --> DevOps
    DevOps --> FinalReport"""
        
        artifact_manager.save_artifact(
            stage=ArtifactFolders.DIAGRAMS,
            base_name="workflow",
            content=workflow_mmd,
            ext="mmd"
        )
        
        # 2. Pipeline Diagram
        pipeline_mmd = """graph LR
    subgraph Requirements
        RA[Requirement Analyst]
    end
    subgraph Design
        SA[Solution Architect]
        BE[Backend Engineer]
    end
    subgraph Implementation
        AISE[AI Software Engineer]
    end
    subgraph Validation
        QA[QA Testing]
        SEC[Security Audit]
        CR[Code Review]
    end
    
    RA --> SA
    SA --> BE
    BE --> AISE
    AISE --> QA
    AISE --> SEC
    AISE --> CR"""
        
        artifact_manager.save_artifact(
            stage=ArtifactFolders.DIAGRAMS,
            base_name="pipeline",
            content=pipeline_mmd,
            ext="mmd"
        )
        
        # 3. Architecture Diagram (Placeholder representing typical stack)
        architecture_mmd = """graph TD
    subgraph Frontend
        React[React / Next.js]
    end
    subgraph Backend
        FastAPI[FastAPI / Node.js]
    end
    subgraph Data
        PG[(PostgreSQL)]
        Redis[(Redis Cache)]
    end
    
    React <-->|REST / GraphQL| FastAPI
    FastAPI <--> PG
    FastAPI <--> Redis"""
        
        artifact_manager.save_artifact(
            stage=ArtifactFolders.DIAGRAMS,
            base_name="architecture",
            content=architecture_mmd,
            ext="mmd"
        )
