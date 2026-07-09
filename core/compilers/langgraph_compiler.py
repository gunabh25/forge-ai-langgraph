"""Compiler for translating ExecutionGraphs into LangGraph StateGraphs."""

from typing import cast, Any
from langgraph.graph import StateGraph, END
from app.state import ForgeState
from core.models.execution_graph import ExecutionGraph
from core.agent_registry import AgentRegistry
from core.workflow_events import WorkflowEventManager, EventTypes
from core.observability import ExecutionObserver
from config.logging import get_logger

logger = get_logger("core.compilers.langgraph_compiler")

class LangGraphCompiler:
    """Translates a framework-independent ExecutionGraph into a LangGraph application."""
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.event_manager = WorkflowEventManager()
        
    def _create_dynamic_node(self, agent_name: str):
        """Creates a state-wrapped execution node compatible with LangGraph."""
        agent = self.registry.get(agent_name)
        if not agent:
            raise ValueError(f"Compiler Error: Agent '{agent_name}' not found in registry.")
            
        def node(state: ForgeState) -> dict:
            logger.info(f"[LangGraph Engine] Executing node: {agent_name}")
            self.event_manager.publish(EventTypes.AGENT_STARTED, {"stage": agent_name, "state": state})
            
            reasoning_logs = []
            def on_llm_completed(payload: dict):
                reasoning_logs.append({
                    "agent": agent_name,
                    "reasoning": payload.get("reasoning", "")
                })
                
            self.event_manager.subscribe(EventTypes.LLM_COMPLETED, on_llm_completed)
            
            try:
                with ExecutionObserver(agent_name, state) as observer:
                    # pyrefly: ignore [unnecessary-type-conversion]
                    result = agent.run(state) # type: ignore
                    
                    if result is None:
                        result = {}
                        
                    if reasoning_logs:
                        result["reasoning_logs"] = reasoning_logs
                        
                    result = observer.finalize(result)
            except Exception as e:
                logger.error(f"[LangGraph Engine] Error executing {agent_name}: {e}")
                raise
            finally:
                self.event_manager.unsubscribe(EventTypes.LLM_COMPLETED, on_llm_completed)
                
            self.event_manager.publish(EventTypes.AGENT_COMPLETED, {"stage": agent_name, "result": result})
            result["current_stage"] = agent_name
            return result
            
        return node
        
    def compile(self, execution_graph: ExecutionGraph) -> Any:
        """
        Translates the ExecutionGraph into a LangGraph StateGraph.
        """
        logger.info(f"LangGraphCompiler starting translation of {len(execution_graph.nodes)} nodes.")
        
        # pyrefly: ignore [bad-specialization]
        workflow = StateGraph(ForgeState)
        
        # 1. Add Nodes
        for node_name, _ in execution_graph.nodes.items():
            workflow.add_node(node_name, self._create_dynamic_node(node_name))
            
        # 2. Set Entry Point
        if execution_graph.entry_node:
            workflow.set_entry_point(execution_graph.entry_node)
            
        # 3. Add Edges
        conditional_edges = {}
        standard_edges = []
        
        for edge in execution_graph.edges:
            target = END if edge.target == "EXIT" else edge.target
            if edge.condition:
                if edge.source not in conditional_edges:
                    conditional_edges[edge.source] = {}
                conditional_edges[edge.source][edge.condition] = target
            else:
                standard_edges.append((edge.source, target))
                
        # Add standard edges
        for source, target in standard_edges:
            workflow.add_edge(source, target)
            
        # Add conditional edges
        for source, conditions in conditional_edges.items():
            # Domain specific logic wrapper for "retry_requested" metadata
            def create_router(src=source, routing_map=conditions):
                def route(state: ForgeState) -> str:
                    metadata = state.get("metadata", {})
                    # Hardcoded logic mapping for UML Validator retries for now
                    if metadata.get("retry_requested") and "retry" in routing_map:
                        return "retry"
                    if "continue" in routing_map:
                        return "continue"
                    # Default fallback
                    return list(routing_map.keys())[0] if routing_map else ""
                return route
                
            workflow.add_conditional_edges(source, create_router(source, conditions), conditions)
            
        # 4. Handle exit nodes explicitly if no outward edge exists
        for node_name in execution_graph.nodes:
            has_outward = any(e.source == node_name for e in execution_graph.edges)
            if not has_outward:
                workflow.add_edge(node_name, END)
                
        logger.info("LangGraph compilation complete.")
        return workflow.compile()
