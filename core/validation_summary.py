"""Validation Summary Generator.

Aggregates QA, Security, and Code Review reports into a single
human-readable Validation Summary Markdown document.
"""

import re
from typing import Optional


class ValidationSummaryGenerator:
    """Generates the ForgeAI Validation Summary from individual agent reports."""

    @staticmethod
    def generate(
        qa_report: Optional[str],
        security_report: Optional[str],
        review_report: Optional[str],
        qa_score: Optional[int],
        security_score: Optional[int],
        review_score: Optional[int],
        overall_score: Optional[int] = None,
        deployment_status: Optional[str] = None,
        deployment_emoji: Optional[str] = None,
    ) -> str:
        """Generate the Validation Summary markdown document.

        Args:
            qa_report: QA Engineer full report text.
            security_report: Security Engineer full report text.
            review_report: Code Reviewer full report text.
            qa_score: QA numeric score (0-100).
            security_score: Security numeric score (0-100).
            review_score: Code Review numeric score (0-100).
            overall_score: Pre-calculated overall quality score.
            deployment_status: Pre-calculated deployment status string.
            deployment_emoji: Status emoji (🟢 / 🟡 / 🔴).

        Returns:
            Formatted Markdown string.
        """
        lines = [
            "# ForgeAI Validation Summary",
            "",
            "====================================",
            "",
            "## Implementation",
            "",
            "✅ Complete",
            "",
            "## Validation Scores",
            "",
            f"- QA: {qa_score if qa_score is not None else 'N/A'}/100",
            f"- Security: {security_score if security_score is not None else 'N/A'}/100",
            f"- Code Review: {review_score if review_score is not None else 'N/A'}/100",
        ]

        if overall_score is not None and deployment_status and deployment_emoji:
            lines += [
                "",
                "--------------------------------",
                f"- Overall: {overall_score}/100",
                f"- Status: {deployment_emoji} {deployment_status}",
            ]

        lines += [
            "",
            "====================================",
            "",
            "## Recommendations",
            "",
        ]

        # Extract top bullet-point recommendations from each report
        recommendations = []
        for report_name, report in [
            ("QA", qa_report),
            ("Security", security_report),
            ("Code Review", review_report),
        ]:
            if not report:
                continue
            bullets = re.findall(r"^[\-\*•]\s+(.+)$", report, re.MULTILINE)
            for bullet in bullets[:2]:
                bullet = bullet.strip()
                if bullet:
                    recommendations.append(f"• [{report_name}] {bullet}")

        if recommendations:
            lines.extend(recommendations)
        else:
            lines.append("• No specific recommendations at this time.")

        lines += [
            "",
            "====================================",
        ]
        return "\n".join(lines)
