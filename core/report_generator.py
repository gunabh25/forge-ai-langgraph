"""Final Project Report Generator for ForgeAI."""

from typing import Dict, Any, List
from datetime import datetime
from app.state import ForgeState
from core.utils import generate_timestamp
import math

class ReportGenerator:
    """Generates the ForgeAI Final Report summarizing the complete workflow."""

    @staticmethod
    def calculate_metrics(state: ForgeState) -> Dict[str, Any]:
        """Calculates workflow execution metrics from the ForgeState.
        
        Args:
            state: The current ForgeState.
            
        Returns:
            A dictionary containing calculated metrics.
        """
        metrics = {}
        
        # Calculate execution time
        metadata = state.get("metadata", {})
        started_at_str = metadata.get("started_at")
        
        execution_time_str = "N/A"
        if started_at_str:
            try:
                # Format: "YYYY-MM-DDTHH:MM:SSZ"
                started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
                ended_at = datetime.fromisoformat(generate_timestamp().replace("Z", "+00:00"))
                delta = ended_at - started_at
                
                hours, remainder = divmod(delta.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                
                parts = []
                if hours > 0:
                    parts.append(f"{int(hours)}h")
                if minutes > 0 or hours > 0:
                    parts.append(f"{int(minutes)}m")
                parts.append(f"{int(seconds)}s")
                
                execution_time_str = " ".join(parts) if parts else "0s"
            except (ValueError, TypeError):
                pass
                
        metrics["workflow_execution_time"] = execution_time_str
        
        # Count artifacts generated
        artifacts = state.get("artifacts", {})
        total_artifacts = sum(len(paths) for paths in artifacts.values())
        metrics["generated_artifacts_count"] = total_artifacts
        
        # Count generated files
        generated_files = state.get("generated_files", {})
        metrics["generated_files_count"] = len(generated_files)
        
        # Count agents executed and parallel executions
        messages = state.get("messages", [])
        agent_names = set()
        for msg in messages:
            if hasattr(msg, "name") and msg.name:
                agent_names.add(msg.name)
        
        # Basic assumptions for counts based on milestone
        metrics["agents_executed"] = len(agent_names)
        
        # QA, Security, Code Review run in parallel
        has_parallel = all(a in agent_names for a in ["qa_engineer", "security_engineer", "code_reviewer"])
        metrics["parallel_executions"] = 1 if has_parallel else 0
        
        # Count approval gates completed
        approval_history = state.get("approval_history", [])
        # We can also add Quality Gate to this if it's stored
        gates = len(approval_history)
        if state.get("quality_gate_status"):
            gates += 1
        metrics["approval_gates_completed"] = gates
        
        # Estimate time saved (approx 4 hours per file, 1 hour per artifact)
        estimated_hours = (len(generated_files) * 4) + (total_artifacts * 1)
        # Cap or format sensibly
        metrics["estimated_time_saved"] = f"{estimated_hours} Hours"
        
        # Project status
        status = state.get("deployment_status", "UNKNOWN")
        emoji = state.get("deployment_emoji", "")
        metrics["project_status"] = f"{emoji} {status}".strip()
        
        return metrics

    @staticmethod
    def generate(state: ForgeState) -> str:
        """Generates the ForgeAI Final Report markdown.
        
        Args:
            state: The current ForgeState containing all outputs and scores.
            
        Returns:
            The formatted markdown string of the final report.
        """
        metrics = ReportGenerator.calculate_metrics(state)
        
        # Extract checkmarks
        reqs = "✅" if state.get("requirements") else "❌"
        arch = "✅" if state.get("architecture") else "❌"
        back = "✅" if state.get("backend_blueprint") else "❌"
        impl = "✅" if state.get("implementation") or state.get("generated_files") else "❌"
        dep = "READY" if state.get("deployment_blueprint") or state.get("production_readiness_report") else "N/A"
        
        # Extract scores
        qa_score = state.get("qa_score", "N/A")
        sec_score = state.get("security_score", "N/A")
        rev_score = state.get("review_score", "N/A")
        overall = state.get("overall_quality_score", "N/A")
        
        # Extensible metrics for the future
        performance_score = state.get("metadata", {}).get("performance_score", "N/A")
        accessibility_score = state.get("metadata", {}).get("accessibility_score", "N/A")
        
        lines = [
            "================================================",
            "",
            "ForgeAI Final Report",
            "",
            f"Requirements        {reqs}",
            "",
            f"Architecture        {arch}",
            "",
            f"Backend             {back}",
            "",
            f"Implementation      {impl}",
            "",
            f"QA                  {qa_score}/100" if str(qa_score).isdigit() else f"QA                  {qa_score}",
            "",
            f"Security            {sec_score}/100" if str(sec_score).isdigit() else f"Security            {sec_score}",
            "",
            f"Review              {rev_score}/100" if str(rev_score).isdigit() else f"Review              {rev_score}",
            "",
            f"Quality             {overall}/100" if str(overall).isdigit() else f"Quality             {overall}",
            "",
            f"Deployment          {dep}",
            "",
            "--------------------------------",
            "",
            "Overall Status",
            "",
            f"{metrics['project_status']}",
            "",
            "Generated Artifacts",
            "",
            f"{metrics['generated_artifacts_count']}",
            "",
            "Generated Files",
            "",
            f"{metrics['generated_files_count']}",
            "",
            "Estimated Development Time Saved",
            "",
            f"{metrics['estimated_time_saved']}",
            "",
            "================================================",
            "",
            "==========================================================",
            "Additional Metrics",
            "==========================================================",
            "",
            f"• Workflow execution duration: {metrics['workflow_execution_time']}",
            f"• Number of AI agents executed: {metrics['agents_executed']}",
            f"• Number of parallel executions: {metrics['parallel_executions']}",
            f"• Number of approval gates completed: {metrics['approval_gates_completed']}",
            f"• Number of artifacts generated: {metrics['generated_artifacts_count']}",
            f"• Number of generated files: {metrics['generated_files_count']}",
            f"• Overall Quality Score: {overall}/100" if str(overall).isdigit() else f"• Overall Quality Score: {overall}",
            f"• Production Readiness Score: {state.get('production_readiness_score', 'N/A')}/100" if str(state.get("production_readiness_score", "")).isdigit() else f"• Production Readiness Score: {state.get('production_readiness_score', 'N/A')}",
            f"• Deployment Status: {metrics['project_status']}",
            ""
        ]
        
        # Append future ready metrics if they exist
        if performance_score != "N/A" or accessibility_score != "N/A":
            lines.extend([
                "==========================================================",
                "Extended Metrics",
                "==========================================================",
                "",
                f"• Performance Score: {performance_score}",
                f"• Accessibility Score: {accessibility_score}",
                ""
            ])
            
        return "\n".join(lines)
