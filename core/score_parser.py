"""Score extraction utility for validation agent reports.

This module provides a shared, stateless utility used by QA, Security, and
Code Review agents to reliably extract numeric scores from LLM-generated
Markdown reports.
"""

import re


class ScoreParser:
    """Extracts numeric quality scores (0-100) from validation report text.

    Tries progressively broader patterns:
      1. "{label}: N/100" — exact label match
      2. "Score: N/100" — any score label
      3. "N/100" — bare fraction anywhere in text

    Falls back to ``default`` if no match is found.
    """

    DEFAULT_SCORE: int = 75

    @classmethod
    def extract(
        cls,
        report_text: str,
        label: str,
        default: int = DEFAULT_SCORE,
    ) -> int:
        """Extract a numeric score from a validation report.

        Args:
            report_text: The full validation report Markdown text.
            label: Score label to search for first (e.g. ``"QA Score"``).
            default: Fallback score in [0, 100] if nothing is found.

        Returns:
            Integer score clamped to [0, 100].
        """
        if not report_text:
            return default

        patterns = [
            # Exact label match: "QA Score: 87/100" or "QA Score 87/100"
            rf"{re.escape(label)}[:\s]+(\d+)\s*/\s*100",
            # Any "Score: N/100" heading
            r"Score[:\s]+(\d+)\s*/\s*100",
            # Bare fraction "N/100" anywhere
            r"(\d+)\s*/\s*100",
        ]

        for pattern in patterns:
            match = re.search(pattern, report_text, re.IGNORECASE)
            if match:
                try:
                    score = int(match.group(1))
                    return max(0, min(100, score))
                except (ValueError, IndexError):
                    continue

        return max(0, min(100, default))
