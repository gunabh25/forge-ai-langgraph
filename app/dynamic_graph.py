"""Dynamic LangGraph StateGraph workflow definition and compilation."""

from typing import Any, Dict, cast
from langgraph.graph import StateGraph, END
from app.state import ForgeState
from core.agent_registry import AgentRegistry
from agents.intent_analyzer.agent import IntentAnalyzerAgent
from agents.planner.agent import PlannerAgent
from config.logging import get_logger
from core.workflow_events import WorkflowEventManager, EventTypes

logger = get_logger("app.dynamic_graph")

class DynamicWorkflowOrchestrator:
    """Orchestrates dynamic intent analysis, planning, and graph compilation."""
    
    def __init__(self):
        self.registry = AgentRegistry()
        self.intent_analyzer = IntentAnalyzerAgent()
        self.planner = PlannerAgent()
        
    def _create_dynamic_node(self, agent_name: str):
        """Creates a node wrapper for a dynamically fetched agent."""
        agent = self.registry.get(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found in registry.")
            
        event_manager = WorkflowEventManager()
        
        def node(state: ForgeState) -> dict:
            logger.info(f"Executing dynamic node: {agent_name}")
            event_manager.publish(EventTypes.AGENT_STARTED, {"stage": agent_name, "state": state})
            
            reasoning_logs = []
            def on_llm_completed(payload: dict):
                reasoning_logs.append({
                    "agent": agent_name,
                    "reasoning": payload.get("reasoning", "")
                })
                
            event_manager.subscribe(EventTypes.LLM_COMPLETED, on_llm_completed)
            
            try:
                # pyrefly: ignore [unnecessary-type-conversion]
                result = agent.run(state) # type: ignore
            except Exception as e:
                logger.error(f"Error executing agent {agent_name}: {e}")
                raise
            finally:
                event_manager.unsubscribe(EventTypes.LLM_COMPLETED, on_llm_completed)
                
            if result is None:
                result = {}
                
            if reasoning_logs:
                result["reasoning_logs"] = reasoning_logs
                
            event_manager.publish(EventTypes.AGENT_COMPLETED, {"stage": agent_name, "result": result})
            
            # Ensure current_stage is tracked
            result["current_stage"] = agent_name
            return result
            
        return node
        
    def execute_workflow(self, state: ForgeState) -> ForgeState:
        """
        Executes the full dynamic pipeline:
        User Prompt -> Intent Analyzer -> Planner -> Dynamic LangGraph Construction -> Execution
        """
        logger.info("Starting Dynamic Workflow pipeline.")
        
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
        
        # 3. Dynamic LangGraph Construction
        # pyrefly: ignore [bad-specialization]
        workflow = StateGraph(ForgeState)
        
        # Add nodes
        for agent_name in execution_plan:
            workflow.add_node(agent_name, self._create_dynamic_node(agent_name))
            
        # Set entry point
        workflow.set_entry_point(execution_plan[0])
        
        # Add sequential edges
        for i in range(len(execution_plan) - 1):
            workflow.add_edge(execution_plan[i], execution_plan[i + 1])
            
        # Finish with END
        workflow.add_edge(execution_plan[-1], END)
        
        # 4. Compile and Execute
        logger.info("Compiling dynamic StateGraph...")
        compiled_app = workflow.compile()
        logger.info("Dynamic StateGraph compiled successfully. Executing...")
        
        # Invoke compiled graph
        final_state = compiled_app.invoke(current_state)
        
        logger.info("Dynamic execution completed.")
        return cast(ForgeState, final_state)
