"""PlantUML Compatibility Layer.

Filters deprecated PlantUML skinparams to prevent warnings and rendering issues
with PlantUML 2024+ versions.

This module is presentation-only. It does NOT modify canonical diagram models
or architectural semantics.
"""

from __future__ import annotations

from typing import List, Set
from config.logging import get_logger

logger = get_logger("agents.uml_generator.plantuml_compatibility")

# Skinparams known to be supported in PlantUML 2024+
SUPPORTED_SKINPARAMS: Set[str] = {
    "nodesep",
    "ranksep",
    "ArrowThickness",
    "ArrowColor",
    "componentStyle",
    "packageStyle",
    "linetype",
    "shadowing",
    "defaultFontName",
    "defaultFontSize",
    "backgroundColor",
    "roundcorner",
    "stereotype",
    "dpi",
    "monochrome",
    "style",
}

# Skinparams deprecated or removed in PlantUML 2024+
DEPRECATED_SKINPARAMS: Set[str] = {
    "handwritten",
    "padding",
    "maxMessageSize",
    "wrapWidth",
}


def filter_skinparams(params: List[str]) -> List[str]:
    """Filter out deprecated PlantUML skinparams.

    Args:
        params: List of skinparam strings (e.g., "skinparam nodesep 60").

    Returns:
        Filtered list with deprecated skinparams removed.
    """
    filtered: List[str] = []
    for param in params:
        param_stripped = param.strip()
        if not param_stripped.startswith("skinparam "):
            filtered.append(param)
            continue

        # Extract the skinparam name (second token)
        tokens = param_stripped.split()
        if len(tokens) >= 2:
            param_name = tokens[1]
            if param_name in DEPRECATED_SKINPARAMS:
                logger.debug("Filtering deprecated skinparam: %s", param_stripped)
                continue

        filtered.append(param)

    return filtered
