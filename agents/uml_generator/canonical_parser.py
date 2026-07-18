"""Canonical Diagram JSON Parser.

Single Source of Truth for normalizing LLM responses, extracting JSON objects
across all supported LLM providers (OpenAI, Gemini, Anthropic, Groq, OpenRouter, Ollama),
and deserializing them into Python dictionaries with detailed diagnostic error propagation.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict
from config.logging import get_logger

logger = get_logger("agents.uml_generator.canonical_parser")


class CanonicalParseError(ValueError):
    """Exception raised when raw LLM response parsing fails."""

    def __init__(self, message: str, stage: str, response_len: int, preview: str):
        super().__init__(message)
        self.stage = stage
        self.response_len = response_len
        self.preview = preview


class CanonicalDiagramParser:
    """Single Source of Truth parser for LLM responses containing Canonical Diagram JSON."""

    @staticmethod
    def parse(response: str | Any) -> Dict[str, Any]:
        """Parse raw LLM response into a clean dictionary.
        
        Args:
            response: Raw LLM string response or existing dictionary object.
            
        Returns:
            Extracted and parsed dictionary object.
            
        Raises:
            CanonicalParseError: If response cannot be parsed into a dictionary.
        """
        # Pass-through if already a dictionary
        if isinstance(response, dict):
            return response

        if not isinstance(response, str):
            raise CanonicalParseError(
                f"Unsupported response type for JSON parsing: {type(response).__name__}",
                stage="type_check",
                response_len=0,
                preview=str(response)[:200],
            )

        stage = "normalization"
        raw_len = len(response)
        preview = response[:200].replace("\n", "\\n")

        # 1. Normalize response: Strip UTF-8 BOM and leading/trailing whitespace
        text = response.lstrip("\ufeff").strip()
        if not text:
            raise CanonicalParseError(
                f"Parsing failed at [{stage}]: Empty response string.",
                stage=stage,
                response_len=raw_len,
                preview=preview,
            )

        stage = "fence_stripping"
        # 2. Extract content from markdown code fences if present (```json ... ``` or ``` ... ```)
        fence_match = re.search(r"```(?:json|puml|plantuml)?\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE)
        if fence_match:
            text = fence_match.group(1).strip()

        stage = "json_object_extraction"
        # 3. Locate outermost curly braces { ... } to handle explanatory text
        first_brace = text.find("{")
        last_brace = text.rfind("}")

        if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
            raise CanonicalParseError(
                f"Parsing failed at [{stage}]: No JSON object bounded by '{{' and '}}' found. "
                f"(length: {raw_len}, start: '{preview}')",
                stage=stage,
                response_len=raw_len,
                preview=preview,
            )

        json_candidate = text[first_brace : last_brace + 1]

        stage = "json_decoding"
        try:
            parsed = json.loads(json_candidate)
            if not isinstance(parsed, dict):
                raise CanonicalParseError(
                    f"Parsing failed at [{stage}]: Parsed JSON root is not an object (got {type(parsed).__name__}). "
                    f"(length: {raw_len}, start: '{preview}')",
                    stage=stage,
                    response_len=raw_len,
                    preview=preview,
                )
            return parsed
        except json.JSONDecodeError as exc:
            raise CanonicalParseError(
                f"Parsing failed at [{stage}]: Invalid JSON syntax - {exc}. "
                f"(length: {raw_len}, start: '{preview}')",
                stage=stage,
                response_len=raw_len,
                preview=preview,
            ) from exc
