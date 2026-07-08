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
        
        # 3. Dynamic LangGraph Construction
        # pyrefly: ignore [bad-specialization]
        workflow = StateGraph(ForgeState)
        
        # Add nodes
        for agent_name in execution_plan:
            workflow.add_node(agent_name, self._create_dynamic_node(agent_name))
            
        # Set entry point
        workflow.set_entry_point(execution_plan[0])
        
        # Add edges
        for i in range(len(execution_plan) - 1):
            current_node = execution_plan[i]
            next_node = execution_plan[i + 1]
            
            if current_node == "UML Validator" and "UML Generator" in execution_plan:
                # Add conditional edge for retries
                def should_retry(state: ForgeState) -> str:
                    metadata = state.get("metadata", {})
                    if metadata.get("retry_requested"):
                        logger.info("Validation failed, retrying UML Generation...")
                        return "retry"
                    return "continue"
                    
                workflow.add_conditional_edges(
                    current_node,
                    should_retry,
                    {
                        "retry": "UML Generator",
                        "continue": next_node
                    }
                )
            else:
                workflow.add_edge(current_node, next_node)
            
        # Finish with END
        if execution_plan[-1] == "UML Validator" and "UML Generator" in execution_plan:
             # Add conditional edge for retries at the end
             def should_retry_end(state: ForgeState) -> str:
                 metadata = state.get("metadata", {})
                 if metadata.get("retry_requested"):
                     logger.info("Validation failed, retrying UML Generation...")
                     return "retry"
                 return "continue"
                 
             workflow.add_conditional_edges(
                 execution_plan[-1],
                 should_retry_end,
                 {
                     "retry": "UML Generator",
                     "continue": END
                 }
             )
        else:
            workflow.add_edge(execution_plan[-1], END)
        
        # 4. Compile and Execute
        logger.info("Compiling dynamic StateGraph...")
        compiled_app = workflow.compile()
        logger.info("Dynamic StateGraph compiled successfully. Executing...")
        
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
