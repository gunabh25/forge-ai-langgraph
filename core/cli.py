"""Command Line Interface Dashboard for ForgeAI using Rich.

Provides real-time visualization of workflow progress, active agents,
and stage status without blocking execution.
"""

import time
from typing import Dict, Any, List, Optional
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.console import Group, Console
from rich.text import Text

from core.workflow_events import WorkflowEventManager, EventTypes
from core.constants import WorkflowStages

class ForgeDashboard:
    """Rich-based real-time dashboard for ForgeAI."""

    def __init__(self):
        self.console = Console()
        self.event_manager = WorkflowEventManager()
        
        # Dashboard state
        self.current_stage = "Initializing"
        self.status_map: Dict[str, str] = {
            WorkflowStages.ENGINEERING_MANAGEMENT: "⬜",
            WorkflowStages.REQUIREMENT_ANALYSIS: "⬜",
            WorkflowStages.SOLUTION_ARCHITECTURE: "⬜",
            WorkflowStages.BACKEND_ENGINEERING: "⬜",
            WorkflowStages.AI_SOFTWARE_ENGINEERING: "⬜",
            WorkflowStages.QA_TESTING: "⬜",
            WorkflowStages.SECURITY_AUDIT: "⬜",
            WorkflowStages.CODE_REVIEW: "⬜",
            WorkflowStages.DEVOPS_ENGINEERING: "⬜"
        }
        
        self.stage_names = {
            WorkflowStages.ENGINEERING_MANAGEMENT: "Engineering Manager",
            WorkflowStages.REQUIREMENT_ANALYSIS: "Requirement Analyst",
            WorkflowStages.SOLUTION_ARCHITECTURE: "Solution Architect",
            WorkflowStages.BACKEND_ENGINEERING: "Backend Engineer",
            WorkflowStages.AI_SOFTWARE_ENGINEERING: "AI Software Engineer",
            WorkflowStages.QA_TESTING: "QA Engineer",
            WorkflowStages.SECURITY_AUDIT: "Security Engineer",
            WorkflowStages.CODE_REVIEW: "Code Reviewer",
            WorkflowStages.DEVOPS_ENGINEERING: "DevOps Engineer"
        }
        
        self.total_stages = len(self.status_map)
        self.completed_stages = 0
        
        self.live: Optional[Live] = None
        self.setup_subscriptions()

    def setup_subscriptions(self):
        """Subscribe to workflow events."""
        self.event_manager.subscribe(EventTypes.AGENT_STARTED, self._on_agent_started)
        self.event_manager.subscribe(EventTypes.AGENT_COMPLETED, self._on_agent_completed)
        self.event_manager.subscribe(EventTypes.WORKFLOW_COMPLETED, self._on_workflow_completed)
        self.event_manager.subscribe(EventTypes.APPROVAL_REQUESTED, self._on_approval)
        # We handle ARTIFACT_GENERATED carefully to pause Live and show preview
        self.event_manager.subscribe(EventTypes.ARTIFACT_GENERATED, self._on_artifact)

    def _on_agent_started(self, payload: Dict[str, Any]):
        stage = payload.get("stage")
        if stage in self.status_map:
            self.status_map[stage] = "🟢"
            self.current_stage = self.stage_names.get(stage, stage)
            self._refresh()

    def _on_agent_completed(self, payload: Dict[str, Any]):
        stage = payload.get("stage")
        if stage in self.status_map:
            self.status_map[stage] = "✅"
            self.completed_stages += 1
            self._refresh()

    def _on_workflow_completed(self, payload: Dict[str, Any]):
        self.current_stage = "Completed"
        # Ensure progress reads 100%
        self.completed_stages = self.total_stages
        self._refresh()
        
    def _on_approval(self, payload):
        self.current_stage = "Waiting for Human Approval..."

        if self.live:
            self.live.update(self._generate_layout())
            self.live.stop()

    def _on_artifact(self, payload: Dict[str, Any]):
        """When an artifact is generated, pause dashboard and show preview."""
        # Wait, if we are in Live mode, we must stop to prompt.
        # But this might be tricky since LangGraph is running synchronously.
        # For this milestone, we use core/artifact_preview.py to handle it.
        # It's better if we just suspend Live.
        path = payload.get("path")
        if self.live and path:
            # We briefly stop live updates
            self.live.stop()
            try:
                from core.artifact_preview import ArtifactPreview
                # pyrefly: ignore [unexpected-keyword]
                ArtifactPreview.display(path, console=self.console)
            except Exception as e:
                self.console.print(f"[red]Error previewing artifact: {e}[/red]")
            finally:
                # Resume live
                self.live.start()

    def _generate_layout(self) -> Group:
        """Generates the Rich renderable layout for the dashboard."""
        # Workflow Progress Table
        table = Table(title="ForgeAI v1.0 - Workflow Progress", box=None, show_header=False)
        table.add_column("Status", justify="center", width=4)
        table.add_column("Agent", style="cyan")
        
        for stage, status in self.status_map.items():
            agent_name = self.stage_names.get(stage, stage)
            if status == "🟢":
                table.add_row(status, f"[bold green]{agent_name}[/bold green] started...")
            elif status == "✅":
                table.add_row(status, f"[dim]{agent_name}[/dim]")
            else:
                table.add_row(status, f"[dim]{agent_name}[/dim]")
                
        progress_pct = 0
        if self.total_stages > 0:
            progress_pct = int((self.completed_stages / self.total_stages) * 100)
            
        progress_bar = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style="green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn()
        )
        task = progress_bar.add_task(f"Current Stage: [yellow]{self.current_stage}[/yellow]", total=100)
        progress_bar.update(task, completed=progress_pct)
        
        main_panel = Panel(
            Group(table, Text(""), progress_bar),
            title="[bold magenta]🚀 ForgeAI Started[/bold magenta]",
            border_style="blue"
        )
        # pyrefly: ignore [bad-return]
        return main_panel

    def _refresh(self):
        """Force the live context to refresh."""
        if self.live:
            self.live.update(self._generate_layout())

    def start(self):
        """Returns a Live context manager to display the dashboard."""
        if hasattr(self.console, "_live_stack"):
            self.console._live_stack.clear()

        self.live = Live(
            self._generate_layout(),
            refresh_per_second=4,
            console=self.console
        )
        return self.live

    def pause(self):
        """Pause the live dashboard before interactive input."""
        if self.live:
            self.live.stop()


    def resume(self):
        """Resume the live dashboard after interactive input."""
        if self.live:
            self.live.start()
            self._refresh()