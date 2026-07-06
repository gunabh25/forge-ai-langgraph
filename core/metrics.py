"""Execution Metrics & Explainability module for ForgeAI."""

# pyrefly: ignore [missing-import]
from rich.console import Console
# pyrefly: ignore [missing-import]
from rich.panel import Panel
# pyrefly: ignore [missing-import]
from rich.table import Table

from core.artifact_manager import ArtifactManager
from core.constants import ArtifactFolders, ArtifactNames
from core.report_generator import ReportGenerator
from app.state import ForgeState

console = Console()

class MetricsTracker:
    """Tracks and displays execution metrics and explainability logs."""

    @staticmethod
    def display_metrics(state: ForgeState):
        """Calculates and prints the final metrics dashboard to the CLI."""
        metrics = ReportGenerator.calculate_metrics(state)
        overall = state.get("overall_quality_score", "N/A")
        
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold white")
        
        table.add_row("Workflow Time", metrics.get("workflow_execution_time", "N/A"))
        table.add_row("Agents Executed", str(metrics.get("agents_executed", "N/A")))
        table.add_row("Generated Files", str(metrics.get("generated_files_count", "N/A")))
        table.add_row("Artifacts", str(metrics.get("generated_artifacts_count", "N/A")))
        table.add_row("Parallel Tasks", str(metrics.get("parallel_executions", "N/A")))
        table.add_row("Quality", f"{overall}/100" if str(overall).isdigit() else str(overall))
        
        # Remove emoji from project status for display
        status = metrics.get("project_status", "UNKNOWN")
        status_clean = " ".join(status.split(" ")[1:]) if status.startswith(tuple("🟢🔴🟡✅❌📄⏳👤🎉⚡")) else status
        table.add_row("Deployment", status_clean)
        
        panel = Panel(table, title="[bold magenta]ForgeAI Metrics[/bold magenta]", border_style="blue")
        console.print(panel)

    @staticmethod
    def generate_reasoning_artifact(state: ForgeState):
        """Generates the engineering decisions markdown from reasoning logs."""
        reasoning_logs = state.get("reasoning_logs", [])
        if not reasoning_logs:
            return
            
        lines = [
            "# Engineering Decisions & Agent Reasoning\n",
            "This document captures the rationale and explainability logs from the AI agents during execution.\n"
        ]
        
        for log in reasoning_logs:
            agent_name = log.get("agent", "Unknown Agent").replace("_", " ").title()
            reasoning = log.get("reasoning", "No explicit reasoning provided.")
            
            lines.append(f"## {agent_name}")
            lines.append(f"**Reasoning**\n{reasoning}\n")
            
        content = "\n".join(lines)
        
        artifact_manager = ArtifactManager()
        artifact_manager.save_artifact(
            stage=ArtifactFolders.REASONING,
            base_name=ArtifactNames.ENGINEERING_DECISIONS,
            content=content,
            ext="md"
        )
