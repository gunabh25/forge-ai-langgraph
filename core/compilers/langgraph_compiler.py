"""Compiler for translating ExecutionGraphs into LangGraph StateGraphs."""

from typing import cast, Any
from langgraph.graph import StateGraph, END
from langgraph.types import Send
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
        for node_name, node_def in execution_graph.nodes.items():
            if node_def.sub_graph:
                # Compile subgraph and add it as a node
                sub_app = self.compile(node_def.sub_graph)
                
                # Wrap the subgraph to only return fields that are safe to merge (annotated reducers or explicitly merged fields)
                def make_subgraph_wrapper(app):
                    def wrapper(state: ForgeState):
                        full_result = app.invoke(state)
                        # Filter to only return fields that were actually modified by the sub-graph agents
                        # and are annotated with reducers in ForgeState.
                        return {
                            "plantuml_diagrams": full_result.get("plantuml_diagrams"),
                            "plantuml_validation_report": full_result.get("plantuml_validation_report"),
                            "rendered_svg_references": full_result.get("rendered_svg_references"),
                            "diagram_execution_states": full_result.get("diagram_execution_states"),
                            "artifacts": full_result.get("artifacts"),
                            "messages": full_result.get("messages")[-1:] if full_result.get("messages") else [],
                            "metadata": full_result.get("metadata"),
                            "current_stage": full_result.get("current_stage")
                        }
                    return wrapper
                    
                workflow.add_node(f"{node_name}_subgraph", make_subgraph_wrapper(sub_app))
                
                # Add a dummy router node that will trigger the conditional edge
                def dummy_router(state: ForgeState) -> dict:
                    return {"current_stage": node_name}
                workflow.add_node(node_name, dummy_router)
            else:
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
                
        # Handle Fan-Out Edges
        for node_name, node_def in execution_graph.nodes.items():
            if node_def.sub_graph:
                # Check if sequential generation is required (e.g. free-tier API limits)
                from app.settings import settings as _settings
                sequential_mode = _settings.UML_SEQUENTIAL_GENERATION

                if sequential_mode:
                    # Sequential mode: run UML Generator once for all diagrams, no fan-out.
                    # UMLGeneratorAgent.run() iterates diagrams itself when current_diagram_id is None.
                    logger.info(
                        "UML_SEQUENTIAL_GENERATION=true — using sequential diagram generation "
                        "(no parallel fan-out)."
                    )

                    def sequential_router(state: ForgeState, next_node_name=None, _subgraph=f"{node_name}_subgraph"):
                        # Delegate to sub-graph once with the full state (no per-diagram Send).
                        return [Send(_subgraph, state)]

                    outward_edge = next((e for e in execution_graph.edges if e.source == node_name), None)
                    next_node = outward_edge.target if outward_edge else END
                    if next_node == "EXIT":
                        next_node = END

                    workflow.add_conditional_edges(
                        node_name,
                        sequential_router,
                        {"skip": next_node},
                    )
                else:
                    # Parallel mode: fan-out with one Send per diagram.
                    def fan_out_router(state: ForgeState, subgraph_name=f"{node_name}_subgraph"):
                        diagrams = state.get("selected_uml_diagrams") or []
                        change_report = state.get("change_analysis_report") or {}
                        affected_diagrams = {d.lower() for d in change_report.get("affected_diagrams", [])}
                        is_incremental = bool(change_report) and change_report.get("change_type") != "new_project"

                        sends = []
                        for diag in diagrams:
                            diag_id = diag.get("diagram_id", diag.get("diagram", diag.get("type", "unknown")))
                            if is_incremental and diag_id.lower() not in affected_diagrams:
                                continue
                            sends.append(Send(subgraph_name, {**state, "current_diagram_id": diag_id}))
                        return sends if sends else "skip"

                    outward_edge = next((e for e in execution_graph.edges if e.source == node_name), None)
                    next_node = outward_edge.target if outward_edge else END
                    if next_node == "EXIT":
                        next_node = END

                    workflow.add_conditional_edges(
                        node_name,
                        fan_out_router,
                        {"skip": next_node},
                    )

                
                # 2. Edge from subgraph to next node
                # The normal standard_edges list has an edge from node_name to next_node.
                # We need to change that to be from subgraph to next_node.
                for i, (src, tgt) in enumerate(standard_edges):
                    if src == node_name:
                        standard_edges[i] = (f"{node_name}_subgraph", tgt)
        
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
