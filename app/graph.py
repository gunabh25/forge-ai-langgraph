"""LangGraph StateGraph workflow definition and compilation."""

from typing import Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from app.state import ForgeState
from core.constants import WorkflowStages
from agents.engineering_manager.agent import EngineeringManagerAgent
from agents.requirement_analyst.agent import RequirementAnalystAgent
from agents.solution_architect.agent import SolutionArchitectAgent
from agents.backend_engineer.agent import BackendEngineerAgent
from agents.ai_software_engineer.agent import AISoftwareEngineerAgent
from core.approval import CLIApproval, ApprovalInterface
from app.router import WorkflowRouter
from config.logging import get_logger
from core.utils import generate_timestamp
from core.workflow_events import WorkflowEventManager, EventTypes
from core.observability import ExecutionObserver
from core.constants import WorkflowStages, ArtifactNames, ArtifactFolders
from core.artifact_manager import ArtifactManager
from core.report_generator import ReportGenerator

logger = get_logger("app.graph")

def _wrap_agent_node(agent_run_fn, stage_name: str):
    """Wraps an agent execution with event publishing and reasoning capture."""
    event_manager = WorkflowEventManager()
    
    def node(state: ForgeState) -> dict:
        logger.info(f"Executing node: {stage_name}")
        event_manager.publish(EventTypes.AGENT_STARTED, {"stage": stage_name, "state": state})
        
        reasoning_logs = []
        def on_llm_completed(payload: dict):
            reasoning_logs.append({
                "agent": stage_name,
                "reasoning": payload.get("reasoning", "")
            })
            
        event_manager.subscribe(EventTypes.LLM_COMPLETED, on_llm_completed)
        
        try:
            with ExecutionObserver(stage_name, state) as observer:
                result = agent_run_fn(state)
                
                if result is None:
                    result = {}
                    
                if reasoning_logs:
                    result["reasoning_logs"] = reasoning_logs
                    
                result = observer.finalize(result)
        finally:
            event_manager.unsubscribe(EventTypes.LLM_COMPLETED, on_llm_completed)
            
        event_manager.publish(EventTypes.AGENT_COMPLETED, {"stage": stage_name, "result": result})
        return result
        
    return node

def create_engineering_manager_node(agent: EngineeringManagerAgent):
    """Wrapper function to create the node for the Engineering Manager."""
    return _wrap_agent_node(agent.run, WorkflowStages.ENGINEERING_MANAGEMENT)

def create_requirement_analyst_node(agent: RequirementAnalystAgent):
    """Wrapper function to create the node for the Requirement Analyst."""
    return _wrap_agent_node(agent.run, WorkflowStages.REQUIREMENT_ANALYSIS)

def create_solution_architect_node(agent: SolutionArchitectAgent):
    """Wrapper function to create the node for the Solution Architect."""
    return _wrap_agent_node(agent.run, WorkflowStages.SOLUTION_ARCHITECTURE)

def create_human_approval_node(dashboard, approval_interface: Optional[ApprovalInterface] = None):
    """Wrapper function to create the node for Human Approval."""
    event_manager = WorkflowEventManager()
    
    def node(state: ForgeState) -> dict:
        logger.info(f"Executing node: {WorkflowStages.HUMAN_APPROVAL}")
        interface = approval_interface or CLIApproval(dashboard)
        
        # Prepare context for display
        context = {
            "requirements": state.get("requirements", ""),
            "architecture": state.get("architecture", "")
        }
        
        event_manager.publish(EventTypes.APPROVAL_REQUESTED, {"stage": WorkflowStages.HUMAN_APPROVAL})
        
        # Invoke approval interface
        approval_result = interface.request_approval(stage=state.get("current_stage", ""), context=context)
        
        # Build approval record
        record = {
            "stage": state.get("current_stage", ""),
            "decision": approval_result.status,
            "feedback": approval_result.feedback,
            "timestamp": generate_timestamp()
        }
        
        event_manager.publish(EventTypes.APPROVAL_COMPLETED, {"stage": WorkflowStages.HUMAN_APPROVAL, "decision": approval_result.status})
        
        # Return updates
        return {
            "approval_status": approval_result.status,
            "approval_history": [record],
            "current_stage": WorkflowStages.HUMAN_APPROVAL
        }
    return node

def create_backend_engineer_node(agent: BackendEngineerAgent):
    """Wrapper function to create the node for the Backend Engineer."""
    return _wrap_agent_node(agent.run, WorkflowStages.BACKEND_ENGINEERING)

def create_ai_software_engineer_node(agent: AISoftwareEngineerAgent):
    """Wrapper function to create the node for the AI Software Engineer."""
    return _wrap_agent_node(agent.run, WorkflowStages.AI_SOFTWARE_ENGINEERING)

def create_final_report_node():
    """Wrapper function to create the node for Final Report Generation."""
    artifact_manager = ArtifactManager()
    
    def node(state: ForgeState) -> dict:
        logger.info(f"Executing node: {WorkflowStages.FINAL_REPORT_GENERATION}")
        
        # Generate report content
        report_content = ReportGenerator.generate(state)
        
        # Save artifact
        saved_path = artifact_manager.save_artifact(
            stage=ArtifactFolders.REPORTS,
            base_name=ArtifactNames.FINAL_REPORT,
            content=report_content,
            ext="md"
        )
        
        # Calculate metrics for state
        metrics = ReportGenerator.calculate_metrics(state)
        
        # Return state updates
        return {
            "final_report": report_content,
            "artifacts": {
                ArtifactFolders.REPORTS: [saved_path]
            },
            "current_stage": WorkflowStages.FINAL_REPORT_GENERATION,
            "project_status": metrics["project_status"],
            "generated_artifacts_count": metrics["generated_artifacts_count"],
            "generated_files_count": metrics["generated_files_count"],
            "workflow_execution_time": metrics["workflow_execution_time"],
            "agents_executed": metrics["agents_executed"],
            "parallel_executions": metrics["parallel_executions"],
            "approval_gates_completed": metrics["approval_gates_completed"],
            "estimated_time_saved": metrics["estimated_time_saved"]
        }
    return node

def route_next(state: ForgeState) -> str:
    """Conditional router function for LangGraph.
    
    Args:
        state: The current ForgeState.
        
    Returns:
        The target node name or END.
    """
    next_stage = WorkflowRouter.get_next_stage(state)
    if next_stage == "END":
        return END
    return next_stage

def compile_workflow(
    dashboard=None,
    approval_interface=None,
    quality_gate_interface=None
) -> CompiledStateGraph:
    """Build, configure, and compile the StateGraph.
    
    Args:
        approval_interface: Optional custom approval interface to use for human approval gate.
        quality_gate_interface: Optional custom quality gate interface.
        
    Returns:
        Compiled LangGraph StateGraph workflow.
    """
    logger.info("Initializing StateGraph...")
    
    # Initialize the graph with the shared state structure
    # pyrefly: ignore [bad-specialization]
    workflow = StateGraph(ForgeState)
    
    # Instantiate the agents
    em_agent = EngineeringManagerAgent()
    ra_agent = RequirementAnalystAgent()
    sa_agent = SolutionArchitectAgent()
    be_agent = BackendEngineerAgent()
    ase_agent = AISoftwareEngineerAgent()
    
    # Register the nodes
    workflow.add_node(WorkflowStages.ENGINEERING_MANAGEMENT, create_engineering_manager_node(em_agent))
    workflow.add_node(WorkflowStages.REQUIREMENT_ANALYSIS, create_requirement_analyst_node(ra_agent))
    workflow.add_node(WorkflowStages.SOLUTION_ARCHITECTURE, create_solution_architect_node(sa_agent))
    workflow.add_node(WorkflowStages.HUMAN_APPROVAL, create_human_approval_node(dashboard, approval_interface))
    workflow.add_node(WorkflowStages.BACKEND_ENGINEERING, create_backend_engineer_node(be_agent))
    workflow.add_node(WorkflowStages.AI_SOFTWARE_ENGINEERING, create_ai_software_engineer_node(ase_agent))
    workflow.add_node(WorkflowStages.FINAL_REPORT_GENERATION, create_final_report_node())
    
    # Set the entry point
    workflow.set_entry_point(WorkflowStages.ENGINEERING_MANAGEMENT)
    
    # Register conditional edges from Engineering Management node
    workflow.add_conditional_edges(
        WorkflowStages.ENGINEERING_MANAGEMENT,
        route_next,
        {
            END: END,
            WorkflowStages.REQUIREMENT_ANALYSIS: WorkflowStages.REQUIREMENT_ANALYSIS
        }
    )
    
    # Register conditional edges from Requirement Analysis node
    workflow.add_conditional_edges(
        WorkflowStages.REQUIREMENT_ANALYSIS,
        route_next,
        {
            END: END,
            WorkflowStages.SOLUTION_ARCHITECTURE: WorkflowStages.SOLUTION_ARCHITECTURE
        }
    )
    
    # Register conditional edges from Solution Architecture node
    workflow.add_conditional_edges(
        WorkflowStages.SOLUTION_ARCHITECTURE,
        route_next,
        {
            END: END,
            WorkflowStages.HUMAN_APPROVAL: WorkflowStages.HUMAN_APPROVAL
        }
    )
    
    # Register conditional edges from Human Approval node
    workflow.add_conditional_edges(
        WorkflowStages.HUMAN_APPROVAL,
        route_next,
        {
            END: END,
            WorkflowStages.BACKEND_ENGINEERING: WorkflowStages.BACKEND_ENGINEERING,
            WorkflowStages.SOLUTION_ARCHITECTURE: WorkflowStages.SOLUTION_ARCHITECTURE
        }
    )
    
    # Register conditional edges from Backend Engineering node
    workflow.add_conditional_edges(
        WorkflowStages.BACKEND_ENGINEERING,
        route_next,
        {
            END: END,
            WorkflowStages.AI_SOFTWARE_ENGINEERING: WorkflowStages.AI_SOFTWARE_ENGINEERING
        }
    )
    
    # Register conditional edges from AI Software Engineering node
    workflow.add_conditional_edges(
        WorkflowStages.AI_SOFTWARE_ENGINEERING,
        route_next,
        {
            END: END,
            WorkflowStages.FINAL_REPORT_GENERATION: WorkflowStages.FINAL_REPORT_GENERATION
        }
    )
    
    # Register conditional edges from Final Report Generation node
    workflow.add_conditional_edges(
        WorkflowStages.FINAL_REPORT_GENERATION,
        route_next,
        {
            END: END
        }
    )
    
    logger.info("Compiling StateGraph...")
    compiled_app = workflow.compile()
    logger.info("StateGraph compiled successfully.")
    
    return compiled_app
