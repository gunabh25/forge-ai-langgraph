"""Constants used throughout the ForgeAI application."""

class WorkflowStages:
    ENGINEERING_MANAGEMENT = "engineering_management"
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    SOLUTION_ARCHITECTURE = "solution_architecture"
    BACKEND_ENGINEERING = "backend_engineering"
    AI_SOFTWARE_ENGINEERING = "ai_software_engineering"
    QA_TESTING = "qa_testing"
    SECURITY_AUDIT = "security_audit"
    CODE_REVIEW = "code_review"
    VALIDATION_SUMMARY = "validation_summary"
    QUALITY_GATE = "quality_gate"
    DEVOPS_ENGINEERING = "devops_engineering"
    HUMAN_APPROVAL = "human_approval"

class AgentNames:
    ENGINEERING_MANAGER = "engineering_manager"
    REQUIREMENT_ANALYST = "requirement_analyst"
    SOLUTION_ARCHITECT = "solution_architect"
    BACKEND_ENGINEER = "backend_engineer"
    AI_SOFTWARE_ENGINEER = "ai_software_engineer"
    QA_ENGINEER = "qa_engineer"
    SECURITY_ENGINEER = "security_engineer"
    CODE_REVIEWER = "code_reviewer"
    DEVOPS_ENGINEER = "devops_engineer"

class ApprovalStatuses:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"

class ArtifactNames:
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    BACKEND_BLUEPRINT = "backend_blueprint"
    IMPLEMENTATION = "implementation"
    QA_REPORT = "qa_report"
    SECURITY_REPORT = "security_report"
    REVIEW_REPORT = "review_report"
    VALIDATION_SUMMARY = "validation_summary"
    QUALITY_REPORT = "quality_report"
    DEPLOYMENT_BLUEPRINT = "deployment_blueprint"

class ArtifactFolders:
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    BACKEND = "backend"
    IMPLEMENTATION = "implementation"
    QA = "qa"
    SECURITY = "security"
    REVIEW = "review"
    VALIDATION = "validation"
    QUALITY = "quality"
    DEPLOYMENT = "deployment"

class ModelDefaults:
    GEMINI_MODEL = "gemini-2.5-flash"
    TEMPERATURE = 0.2
    MAX_TOKENS = 8192
