"""Dynamic Executor for executing agent plans."""

from typing import Dict, Any, List, cast
from app.state import (
    ForgeState,
    merge_artifacts,
    merge_metadata,
    merge_approval_history,
    merge_reasoning_logs,
    merge_timeline_events,
    merge_generated_files,
    merge_execution_report

)
from core.agent_registry import AgentRegistry
from core.observability import ExecutionObserver
from config.logging import get_logger
from langgraph.graph.message import add_messages

logger = get_logger("core.dynamic_executor")

class DynamicExecutor:
    """Executes a dynamic sequence of agents based on an execution plan."""
    
    def __init__(self):
        self.registry = AgentRegistry()
        
    def execute(self, state: ForgeState, execution_plan: List[str]) -> ForgeState:
        """
        Execute the plan sequentially.
        
        Args:
            state: The initial ForgeState.
            execution_plan: A list of agent names to execute in order.
            
        Returns:
            The final ForgeState after all agents have run.
        """
        logger.info(f"Starting dynamic execution with plan: {execution_plan}")
        
        # Shallow copy is standard for TypedDict state updates
        current_state: Dict[str, Any] = dict(state)
        
        for agent_name in execution_plan:
            logger.info(f"Fetching agent: {agent_name}")
            agent = self.registry.get(agent_name)
            
            if not agent:
                logger.error(f"Agent '{agent_name}' not found in registry. Skipping.")
                continue
                
            try:
                logger.info(f"Executing agent: {agent_name}")
                with ExecutionObserver(agent_name, cast(ForgeState, current_state)) as observer:
                    # Provide type coercion to ForgeState
                    state_updates = agent.run(current_state) # type: ignore
                    state_updates = observer.finalize(state_updates)
                
                # Apply updates according to ForgeState reducers
                if isinstance(state_updates, dict):
                    for key, value in state_updates.items():
                        if key == "artifacts":
                            current_state["artifacts"] = merge_artifacts(
                                cast(Dict[str, List[str]], current_state.get("artifacts", {})), value
                            )
                        elif key == "metadata":
                            current_state["metadata"] = merge_metadata(
                                cast(Dict[str, Any], current_state.get("metadata", {})), value
                            )
                        elif key == "approval_history":
                            current_state["approval_history"] = merge_approval_history(
                                cast(List[Dict[str, Any]], current_state.get("approval_history", [])), value
                            )
                        elif key == "reasoning_logs":
                            current_state["reasoning_logs"] = merge_reasoning_logs(
                                cast(List[Dict[str, str]], current_state.get("reasoning_logs", [])), value
                            )
                        elif key == "timeline_events":
                            current_state["timeline_events"] = merge_timeline_events(
                                cast(List[Dict[str, Any]], current_state.get("timeline_events", [])), value
                            )
                        elif key == "generated_files":
                            current_state["generated_files"] = merge_generated_files(
                                cast(Dict[str, str], current_state.get("generated_files", {})), value
                            )
                        elif key == "messages":
                            current_messages = cast(list, current_state.get("messages", []))
                            current_state["messages"] = add_messages(current_messages, value)
                        elif key == "execution_report":
                            current_state["execution_report"] = merge_execution_report(
                                cast(Dict[str, Any], current_state.get("execution_report", {})), value
                            )
                        else:
                            current_state[key] = value
                
            except Exception as e:
                logger.error(f"Agent '{agent_name}' execution failed: {e}")
                # We stop the dynamic execution if an agent fails to preserve order and correctness
                break
                
        logger.info("Dynamic execution completed.")
        return cast(ForgeState, current_state)
