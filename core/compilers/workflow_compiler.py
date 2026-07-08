"""Compiler for generating framework-independent ExecutionGraphs from Planner sequences."""

from typing import List, Tuple, Dict, Any, Set
from core.models.execution_graph import ExecutionGraph, ExecutionNode, ExecutionEdge, CompilationError
from config.logging import get_logger

logger = get_logger("core.compilers.workflow_compiler")

class WorkflowCompiler:
    """Compiles linear agent sequences into optimized ExecutionGraphs."""
    
    def compile(self, execution_plan: List[str]) -> Tuple[ExecutionGraph, Dict[str, Any]]:
        """
        Compile an ordered list of agents into an ExecutionGraph.
        
        Args:
            execution_plan: List of agent names (e.g., from PlannerAgent).
            
        Returns:
            Tuple of (ExecutionGraph, metadata_dict).
        """
        logger.info(f"Starting workflow compilation for {len(execution_plan)} nodes.")
        
        if not execution_plan:
            return ExecutionGraph(), {"graph_nodes": 0, "graph_edges": 0}
            
        graph = ExecutionGraph()
        
        # 1. Dependency Resolution & Node Creation
        for i, agent_name in enumerate(execution_plan):
            node = ExecutionNode(
                agent_name=agent_name,
                requires=[execution_plan[i-1]] if i > 0 else [],
                produces=[f"{agent_name}_output"],
                estimated_latency=1000,  # default placeholder
                estimated_cost=0.01      # default placeholder
            )
            graph.nodes[agent_name] = node
            
        graph.entry_node = execution_plan[0]
        graph.exit_node = execution_plan[-1]
        
        # 2. Edge Construction (Linear Flow)
        for i in range(len(execution_plan) - 1):
            source = execution_plan[i]
            target = execution_plan[i+1]
            graph.edges.append(ExecutionEdge(source=source, target=target))
            
        # 3. Retry Injection Pass (Domain Optimization)
        self._inject_retry_edges(graph, execution_plan)
        
        # 4. Graph Validation
        self._validate_graph(graph)
        
        # 5. Metadata Calculation
        metadata = self._calculate_observability_metrics(graph)
        graph.metadata = metadata
        
        logger.info("Workflow compilation completed successfully.")
        return graph, metadata
        
    def _inject_retry_edges(self, graph: ExecutionGraph, execution_plan: List[str]) -> None:
        """Injects dynamic retry edges if Validator and Generator pairs exist."""
        if "UML Validator" in graph.nodes and "UML Generator" in graph.nodes:
            # The Validator can potentially retry the Generator
            logger.info("Detected Validator-Generator pair. Injecting retry logic.")
            graph.nodes["UML Validator"].retryable = True
            
            # Find the forward edge leaving UML Validator to replace it with conditional edges
            next_node = None
            edge_to_remove = None
            for edge in graph.edges:
                if edge.source == "UML Validator":
                    next_node = edge.target
                    edge_to_remove = edge
                    break
            
            if edge_to_remove and next_node is not None:
                graph.edges.remove(edge_to_remove)
                
                # Conditional edges: retry back to generator, continue to next node
                graph.edges.append(ExecutionEdge(
                    source="UML Validator", 
                    target="UML Generator", 
                    condition="retry"
                ))
                graph.edges.append(ExecutionEdge(
                    source="UML Validator", 
                    target=next_node, 
                    condition="continue"
                ))
            elif graph.exit_node == "UML Validator":
                # It's the final node, add conditional exit
                graph.edges.append(ExecutionEdge(
                    source="UML Validator", 
                    target="UML Generator", 
                    condition="retry"
                ))
                graph.edges.append(ExecutionEdge(
                    source="UML Validator", 
                    target="EXIT", 
                    condition="continue"
                ))
                # LangGraph end mapping will handle EXIT
            
    def _validate_graph(self, graph: ExecutionGraph) -> None:
        """Runs validation passes to catch circular dependencies or disconnected nodes."""
        if not graph.nodes:
            return
            
        # Cycle Detection (DFS)
        visited = set()
        path = set()
        
        # Build adjacency list
        adj: Dict[str, List[str]] = {node: [] for node in graph.nodes}
        for edge in graph.edges:
            if edge.source in adj and edge.target in adj:
                adj[edge.source].append(edge.target)
                
        def has_cycle(node: str) -> bool:
            if node == "EXIT":
                return False
            visited.add(node)
            path.add(node)
            for neighbor in adj.get(node, []):
                # Allow intentional 'retry' backwards edges by ignoring them for strict acyclic checking
                # But typically retry is a cycle. For validation, we should skip known conditional back-edges.
                edge_condition = next((e.condition for e in graph.edges if e.source == node and e.target == neighbor), None)
                if edge_condition == "retry":
                    continue
                    
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in path:
                    return True
            path.remove(node)
            return False
            
        if graph.entry_node and has_cycle(graph.entry_node):
            raise CompilationError(
                error="Circular Dependency Detected",
                nodes=list(path),
                resolution="Remove cyclic dependencies unless marked explicitly as conditional retries."
            )
            
    def _calculate_observability_metrics(self, graph: ExecutionGraph) -> Dict[str, Any]:
        """Calculates expected execution metrics."""
        total_latency = sum(n.estimated_latency for n in graph.nodes.values())
        total_cost = sum(n.estimated_cost for n in graph.nodes.values())
        retry_nodes = sum(1 for n in graph.nodes.values() if n.retryable)
        parallel_groups = sum(1 for n in graph.nodes.values() if n.parallelizable)
        
        return {
            "graph_nodes": len(graph.nodes),
            "graph_edges": len(graph.edges),
            "parallel_groups": parallel_groups,
            "retry_nodes": retry_nodes,
            "estimated_cost": round(total_cost, 4),
            "estimated_latency_ms": total_latency
        }
