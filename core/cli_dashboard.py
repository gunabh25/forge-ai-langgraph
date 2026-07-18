"""CLI Dashboard for real-time workflow observability."""

import time
import rich.box
from rich.console import Console
from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel
from core.workflow_events import WorkflowEventManager, EventTypes
from typing import Dict, Any, List, Optional

class CLIDashboard:
    """Subscribes to workflow events and renders a real-time CLI dashboard using Rich."""
    def __init__(self):
        self.console = Console()
        self.event_manager = WorkflowEventManager()
        
        # State tracking
        self.workflow_id = "N/A"
        self.provider = "N/A"
        self.model = "N/A"
        self.start_time = 0.0
        self.end_time = 0.0
        self.agents_executed = 0
        self.llm_calls = 0
        self.repair_attempts = 0
        self.generated_artifacts = 0
        self.successful_diagrams = 0
        self.failed_diagrams = 0
        self.diagram_scores: List[float] = []
        self.production_ready_count = 0
        
        self.tree: Optional[Tree] = None
        self.current_agent_node = None
        self.diagram_nodes = {}
        
    def start(self):
        """Start listening to events."""
        self.event_manager.subscribe("*", self._on_event)
        
    def stop(self):
        """Stop listening to events."""
        self.event_manager.unsubscribe("*", self._on_event)

    def _on_event(self, payload: Dict[str, Any]):
        try:
            event_type = payload.get("event_type")
            
            if event_type == EventTypes.WORKFLOW_STARTED:
                self.workflow_id = payload.get("workflow_id", "Unknown")
                self.start_time = payload.get("timestamp", time.time())
                self.tree = Tree(f"[bold blue]Workflow Execution[/bold blue] ({self.workflow_id})")
                self.console.print(f"\n[bold green]Starting Workflow:[/bold green] {self.workflow_id}\n")
                
            elif event_type == EventTypes.AGENT_STARTED:
                agent = payload.get("agent", "Unknown")
                if self.tree is not None:
                    self.current_agent_node = self.tree.add(f"[bold cyan]▶ {agent}[/bold cyan]")
                self.console.print(f"[cyan]▶[/cyan] {agent}")
                
            elif event_type == EventTypes.AGENT_COMPLETED:
                agent = payload.get("agent", "Unknown")
                latency = payload.get("latency_ms", 0) / 1000.0
                status = payload.get("status", "success")
                self.agents_executed += 1
                if status == "success":
                    self.console.print(f"  [green]✓ Completed ({latency:.1f} sec)[/green]")
                else:
                    self.console.print(f"  [red]✗ Failed ({latency:.1f} sec)[/red]")
                    
            elif event_type == EventTypes.LLM_STARTED:
                self.provider = payload.get("provider", self.provider)
                self.model = payload.get("model", self.model)
                
            elif event_type == EventTypes.LLM_COMPLETED:
                self.llm_calls += 1
                
            elif event_type == EventTypes.RENDERER_STARTED:
                diag = payload.get("diagram", "Unknown")
                self.console.print(f"  Generating {diag}...")
                if self.current_agent_node is not None:
                    self.diagram_nodes[diag] = self.current_agent_node.add(f"[yellow]{diag}[/yellow]")
                    
            elif event_type == EventTypes.RENDERER_COMPLETED:
                diag = payload.get("diagram", "Unknown")
                status = payload.get("status", "success")
                score = payload.get("diagram_score")
                if score is not None:
                    self.diagram_scores.append(float(score))
                    if score >= 90.0:
                        self.production_ready_count += 1
                if status == "success":
                    self.successful_diagrams += 1
                    self.console.print(f"  [green]Rendered {diag}[/green]")
                else:
                    self.failed_diagrams += 1
                    self.console.print(f"  [red]Failed {diag}: {payload.get('reason')}[/red]")
                    
            elif event_type == EventTypes.REPAIR_STARTED:
                self.repair_attempts += 1
                
            elif event_type == EventTypes.WORKFLOW_COMPLETED:
                self.end_time = payload.get("timestamp", time.time())
                summary_data = payload.get("summary", {})
                if summary_data:
                    if "total_repair_attempts" in summary_data:
                        self.repair_attempts = summary_data["total_repair_attempts"]
                    if "production_ready_count" in summary_data:
                        self.production_ready_count = summary_data["production_ready_count"]
                    if "successful_diagrams" in summary_data:
                        self.successful_diagrams = summary_data["successful_diagrams"]
                    if "failed_diagrams" in summary_data:
                        self.failed_diagrams = summary_data["failed_diagrams"]
                    if "average_diagram_score" in summary_data:
                        self.diagram_scores = [float(summary_data["average_diagram_score"])]
                self._render_dashboard()
        except Exception as e:
            pass # Failsafe against rich formatting errors
            
    def _render_dashboard(self):
        self.console.print("\n")
        if self.tree is not None:
            self.console.print(self.tree)
            self.console.print("\n")
            
        table = Table(title="[bold]Execution Summary[/bold]", show_header=False, box=rich.box.SIMPLE_HEAVY)
        table.add_column("Metric", style="cyan", justify="right")
        table.add_column("Value", style="white")
        
        duration = self.end_time - self.start_time if self.start_time else 0.0
        avg_score = f"{(sum(self.diagram_scores) / len(self.diagram_scores)):.1f}" if self.diagram_scores else "100.0"
        
        table.add_row("Workflow ID", self.workflow_id)
        table.add_row("Execution Time", f"{duration:.2f} sec")
        table.add_row("Provider", self.provider)
        table.add_row("Model", self.model)
        table.add_row("Agents Executed", str(self.agents_executed))
        table.add_row("LLM Calls", str(self.llm_calls))
        table.add_row("Repair Attempts", str(self.repair_attempts))
        table.add_row("Successful Diagrams", f"[green]{self.successful_diagrams}[/green]")
        table.add_row("Failed Diagrams", f"[red]{self.failed_diagrams}[/red]")
        table.add_row("Average Diagram Score", f"[magenta]{avg_score}[/magenta]")
        table.add_row("Production Ready Count", f"[cyan]{self.production_ready_count}/{self.successful_diagrams + self.failed_diagrams}[/cyan]")
        
        self.console.print(Panel(table, border_style="blue"))
