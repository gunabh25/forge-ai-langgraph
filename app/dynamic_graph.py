"""Dynamic LangGraph StateGraph workflow definition and compilation."""

from typing import Any, Dict, cast
import time
import uuid
from langgraph.graph import StateGraph, END
from app.state import ForgeState
from core.agent_registry import AgentRegistry
from agents.intent_analyzer.agent import IntentAnalyzerAgent
from agents.planner.agent import PlannerAgent
from config.logging import get_logger
from core.workflow_events import WorkflowEventManager, EventTypes
from core.compilers.workflow_compiler import WorkflowCompiler
from core.compilers.langgraph_compiler import LangGraphCompiler

logger = get_logger("app.dynamic_graph")

class DynamicWorkflowOrchestrator:
    """Orchestrates dynamic intent analysis, planning, and graph compilation."""
    
    def __init__(self):
        self.registry = AgentRegistry()
        self.intent_analyzer = IntentAnalyzerAgent()
        self.planner = PlannerAgent()
        
    def execute_workflow(self, state: ForgeState) -> ForgeState:
        """
        Executes the full dynamic pipeline:
        User Prompt -> Intent Analyzer -> Planner -> Dynamic LangGraph Construction -> Execution
        """
        logger.info("Starting Dynamic Workflow pipeline.")
        
        start_time = time.time()
        
        # Cast to dict for manual updates
        current_state = cast(dict, state)
        
        # 1. Intent Analysis
        logger.info("Running Intent Analyzer...")
        intent_result = self.intent_analyzer.run(state)
        if isinstance(intent_result, dict):
            current_state.update(intent_result)
            
        # 2. Planner
        logger.info("Running Planner...")
        planner_result = self.planner.run(cast(ForgeState, current_state))
        if isinstance(planner_result, dict):
            current_state.update(planner_result)
            
        execution_plan = current_state.get("execution_plan", [])
        if not execution_plan:
            logger.warning("Execution plan is empty! Nothing to execute.")
            return cast(ForgeState, current_state)
            
        logger.info(f"Generated Execution Plan: {execution_plan}")
        
        # 3. Dynamic Compilation Pipeline
        logger.info("Executing Workflow Compiler passes...")
        workflow_compiler = WorkflowCompiler()
        execution_graph, compilation_metadata = workflow_compiler.compile(execution_plan)
        
        logger.info(f"Compilation Metadata: {compilation_metadata}")
        if "metadata" not in current_state:
            current_state["metadata"] = {}
        current_state["metadata"]["compilation_metrics"] = compilation_metadata
        
        logger.info("Translating ExecutionGraph to LangGraph...")
        langgraph_compiler = LangGraphCompiler(self.registry)
        compiled_app = langgraph_compiler.compile(execution_graph)
        
        # Invoke compiled graph
        final_state = compiled_app.invoke(current_state)
        
        end_time = time.time()
        execution_time_ms = int((end_time - start_time) * 1000)
        
        execution_report = {
            "execution_id": str(uuid.uuid4()),
            "workflow_type": final_state.get("intent_classification", {}).get("primary_intent", "unknown"),
            "agents_executed": execution_plan,
            "execution_time_ms": execution_time_ms,
            "llm_calls": len(final_state.get("reasoning_logs", [])),
            "validation_retries": 0, # Placeholder unless tracked via explicit metadata flag count
            "generated_diagrams": len(final_state.get("uml_recommendation_report", {}).get("selected_diagrams", [])),
            "artifacts": final_state.get("artifacts", {}),
            "status": "success"
        }
        
        final_state["execution_report"] = execution_report
        
        logger.info("Dynamic execution completed.")
        return cast(ForgeState, final_state)
