"""Compiler for generating framework-independent ExecutionGraphs from Planner sequences."""

from typing import List, Tuple, Dict, Any, Set, Optional
from core.models.execution_graph import ExecutionGraph, ExecutionNode, ExecutionEdge, CompilationError
from config.logging import get_logger

logger = get_logger("core.compilers.workflow_compiler")

class WorkflowCompiler:
    """Compiles linear agent sequences into optimized ExecutionGraphs."""
    
    def compile(self, execution_plan: List[str], execution_strategy: Optional[Dict[str, Any]] = None) -> Tuple[ExecutionGraph, Dict[str, Any]]:
        """
        Compile an ordered list of agents into an ExecutionGraph.
        
        Args:
            execution_plan: List of agent names (e.g., from PlannerAgent).
            execution_strategy: Dictionary with parallelization strategy.
            
        Returns:
            Tuple of (ExecutionGraph, metadata_dict).
        """
        logger.info(f"Starting workflow compilation for {len(execution_plan)} nodes.")
        
        if not execution_plan:
            return ExecutionGraph(), {"graph_nodes": 0, "graph_edges": 0}
            
        # Collapse parallel agents into a single Fan-Out node if strategy is provided
        processed_plan = []
        sub_plan = []
        if execution_strategy and "parallelizable_agents" in execution_strategy:
            parallelizable = set(execution_strategy["parallelizable_agents"])
            for agent in execution_plan:
                if agent in parallelizable:
                    sub_plan.append(agent)
                else:
                    processed_plan.append(agent)
                    
            if sub_plan:
                processed_plan.append("UML Parallel Pipeline")
        else:
            processed_plan = execution_plan.copy()
            
        graph = ExecutionGraph()
        
        # 1. Dependency Resolution & Node Creation
        for i, agent_name in enumerate(processed_plan):
            node = ExecutionNode(
                agent_name=agent_name,
                requires=[processed_plan[i-1]] if i > 0 else [],
                produces=[f"{agent_name}_output"],
                estimated_latency=1000,  # default placeholder
                estimated_cost=0.01      # default placeholder
            )
            
            if agent_name == "UML Parallel Pipeline" and sub_plan:
                node.parallelizable = True
                sub_graph, _ = self.compile(sub_plan)
                node.sub_graph = sub_graph
                
            graph.nodes[agent_name] = node
            
        graph.entry_node = processed_plan[0]
        graph.exit_node = processed_plan[-1]
        
        # 2. Edge Construction (Linear Flow)
        for i in range(len(processed_plan) - 1):
            source = processed_plan[i]
            target = processed_plan[i+1]
            graph.edges.append(ExecutionEdge(source=source, target=target))
            
        # 3. Retry Injection Pass (Domain Optimization)
        if "UML Validator" in graph.nodes:
            self._inject_retry_edges(graph, processed_plan)
        
        # 4. Graph Validation
        self._validate_graph(graph)
        
        # 5. Metadata Calculation
        metadata = self._calculate_observability_metrics(graph)
        graph.metadata = metadata
        
        logger.info("Workflow compilation completed successfully.")
        return graph, metadata
        
    def _inject_retry_edges(self, graph: ExecutionGraph, execution_plan: List[str]) -> None:
        """Injects dynamic retry edges if Validator and Generator pairs exist."""
        if "UML Validator" in graph.nodes:
            logger.info("Detected UML Validator. Injecting UML Repair Agent loop.")
            
            # Inject the Repair node dynamically since Planner may not include conditional failure nodes
            if "UML Repair Agent" not in graph.nodes:
                repair_node = ExecutionNode(
                    agent_name="UML Repair Agent",
                    requires=["plantuml_validation_report", "plantuml_diagrams"],
                    produces=["plantuml_diagrams"],
                    estimated_latency=2000,
                    estimated_cost=0.01,
                    retryable=False
                )
                graph.nodes["UML Repair Agent"] = repair_node
                
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
                
                # Conditional edges: retry back to repair agent, continue to next node
                graph.edges.append(ExecutionEdge(
                    source="UML Validator", 
                    target="UML Repair Agent", 
                    condition="retry"
                ))
                graph.edges.append(ExecutionEdge(
                    source="UML Validator", 
                    target=next_node, 
                    condition="continue"
                ))
                
                # Close the loop from Repair Agent back to Validator
                graph.edges.append(ExecutionEdge(
                    source="UML Repair Agent",
                    target="UML Validator"
                ))
                
            elif graph.exit_node == "UML Validator":
                # It's the final node, add conditional exit
                graph.edges.append(ExecutionEdge(
                    source="UML Validator", 
                    target="UML Repair Agent", 
                    condition="retry"
                ))
                graph.edges.append(ExecutionEdge(
                    source="UML Validator", 
                    target="EXIT", 
                    condition="continue"
                ))
                
                # Close the loop
                graph.edges.append(ExecutionEdge(
                    source="UML Repair Agent",
                    target="UML Validator"
                ))
            
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
