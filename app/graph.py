"""LangGraph StateGraph workflow definition and compilation."""

from typing import Any
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from app.state import ForgeState
from core.constants import WorkflowStages
from agents.engineering_manager.agent import EngineeringManagerAgent
from agents.requirement_analyst.agent import RequirementAnalystAgent
from agents.solution_architect.agent import SolutionArchitectAgent
from app.router import WorkflowRouter
from config.logging import get_logger

logger = get_logger("app.graph")

def create_engineering_manager_node(agent: EngineeringManagerAgent):
    """Wrapper function to create the node for the Engineering Manager.
    
    Args:
        agent: The EngineeringManagerAgent instance.
        
    Returns:
        Callable node function.
    """
    def node(state: ForgeState) -> dict:
        logger.info(f"Executing node: {WorkflowStages.ENGINEERING_MANAGEMENT}")
        return agent.run(state)
    return node

def create_requirement_analyst_node(agent: RequirementAnalystAgent):
    """Wrapper function to create the node for the Requirement Analyst.
    
    Args:
        agent: The RequirementAnalystAgent instance.
        
    Returns:
        Callable node function.
    """
    def node(state: ForgeState) -> dict:
        logger.info(f"Executing node: {WorkflowStages.REQUIREMENT_ANALYSIS}")
        return agent.run(state)
    return node

def create_solution_architect_node(agent: SolutionArchitectAgent):
    """Wrapper function to create the node for the Solution Architect.
    
    Args:
        agent: The SolutionArchitectAgent instance.
        
    Returns:
        Callable node function.
    """
    def node(state: ForgeState) -> dict:
        logger.info(f"Executing node: {WorkflowStages.SOLUTION_ARCHITECTURE}")
        return agent.run(state)
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

def compile_workflow() -> CompiledStateGraph:
    """Build, configure, and compile the StateGraph.
    
    Returns:
        Compiled LangGraph StateGraph workflow.
    """
    logger.info("Initializing StateGraph...")
    
    # Initialize the graph with the shared state structure
    # pyrefly: ignore [bad-specialization]
    workflow = StateGraph(ForgeState)
    
    # Instantiate the agent
    em_agent = EngineeringManagerAgent()
    ra_agent = RequirementAnalystAgent()
    sa_agent = SolutionArchitectAgent()
    
    # Register the nodes
    workflow.add_node(WorkflowStages.ENGINEERING_MANAGEMENT, create_engineering_manager_node(em_agent))
    workflow.add_node(WorkflowStages.REQUIREMENT_ANALYSIS, create_requirement_analyst_node(ra_agent))
    workflow.add_node(WorkflowStages.SOLUTION_ARCHITECTURE, create_solution_architect_node(sa_agent))
    
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
            END: END
        }
    )
    
    logger.info("Compiling StateGraph...")
    compiled_app = workflow.compile()
    logger.info("StateGraph compiled successfully.")
    
    return compiled_app
