"""Targeted Repair Patcher.

Applies localized section patches (relationships, aliases, packages, syntax, layout hints)
to Canonical Diagram JSON models to repair validation failures without full diagram regeneration.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, Field

from schemas.canonical_diagram import (
    BaseCanonicalDiagram,
    ComponentDiagramCanonical,
    SequenceDiagramCanonical,
    Relationship,
    BusinessPackage,
)
from agents.uml_generator.canonical_parser import CanonicalDiagramParser
from config.logging import get_logger

logger = get_logger("agents.uml_repair.targeted_patcher")


class TargetedRepairPatch(BaseModel):
    """Targeted section patch containing localized diagram repair edits."""
    repaired_relationships: Optional[List[Relationship]] = Field(
        None, description="Updated or added relationships"
    )
    removed_relationship_pairs: Optional[List[List[str]]] = Field(
        None, description="List of [source_id, target_id] pairs to remove"
    )
    repaired_packages: Optional[List[BusinessPackage]] = Field(
        None, description="Updated or added business packages"
    )
    repaired_aliases: Optional[Dict[str, str]] = Field(
        None, description="Mapping of element_id -> repaired_display_name"
    )
    removed_participant_ids: Optional[List[str]] = Field(
        None, description="List of illegal/unapproved element IDs to remove"
    )


class TargetedPatcher:
    """Applies TargetedRepairPatch edits to a BaseCanonicalDiagram instance."""

    @classmethod
    def apply_patch(
        cls,
        diagram: BaseCanonicalDiagram,
        patch: TargetedRepairPatch,
    ) -> BaseCanonicalDiagram:
        """Apply targeted section patch to canonical diagram model.
        
        Args:
            diagram: The canonical diagram instance.
            patch: The TargetedRepairPatch containing section edits.
            
        Returns:
            Updated BaseCanonicalDiagram instance.
        """
        # Create a deep copy of diagram model data
        data = diagram.model_dump()
        
        # 1. Handle Removed Participants
        if patch.removed_participant_ids:
            remove_set = set(patch.removed_participant_ids)
            data["actors"] = [a for a in data.get("actors", []) if a["id"] not in remove_set]
            data["external_systems"] = [e for e in data.get("external_systems", []) if e["id"] not in remove_set]
            if "business_capabilities" in data:
                data["business_capabilities"] = [c for c in data["business_capabilities"] if c["id"] not in remove_set]
            if "databases" in data:
                data["databases"] = [d for d in data["databases"] if d["id"] not in remove_set]
            if "participants" in data:
                data["participants"] = [p for p in data["participants"] if p not in remove_set]

        # 2. Handle Repaired Aliases (Display Name Updates)
        if patch.repaired_aliases:
            for elem_list in ("actors", "external_systems", "business_capabilities", "databases"):
                if elem_list in data:
                    for item in data[elem_list]:
                        if item["id"] in patch.repaired_aliases:
                            item["name"] = patch.repaired_aliases[item["id"]]

        # 3. Handle Repaired Packages
        if patch.repaired_packages and "business_packages" in data:
            pkg_map = {p.id: p.model_dump() for p in patch.repaired_packages}
            new_packages = []
            seen_pkg_ids = set()
            for existing_pkg in data["business_packages"]:
                pkg_id = existing_pkg["id"]
                if pkg_id in pkg_map:
                    new_packages.append(pkg_map[pkg_id])
                    seen_pkg_ids.add(pkg_id)
                else:
                    new_packages.append(existing_pkg)
            # Add any new packages from patch
            for new_pkg in patch.repaired_packages:
                if new_pkg.id not in seen_pkg_ids:
                    new_packages.append(new_pkg.model_dump())
            data["business_packages"] = new_packages

        # 4. Handle Relationship Removals
        if patch.removed_relationship_pairs and "relationships" in data:
            remove_pairs = {(pair[0], pair[1]) for pair in patch.removed_relationship_pairs if len(pair) >= 2}
            data["relationships"] = [
                r for r in data["relationships"]
                if (r["source_id"], r["target_id"]) not in remove_pairs
            ]

        # 5. Handle Repaired / Added Relationships
        if patch.repaired_relationships and "relationships" in data:
            rel_dict: Dict[Tuple[str, str], Dict[str, Any]] = {
                (r["source_id"], r["target_id"]): r for r in data["relationships"]
            }
            for rep_rel in patch.repaired_relationships:
                rel_dict[(rep_rel.source_id, rep_rel.target_id)] = rep_rel.model_dump()
            data["relationships"] = list(rel_dict.values())

        # Re-instantiate model
        if isinstance(diagram, ComponentDiagramCanonical):
            return ComponentDiagramCanonical.model_validate(data)
        elif isinstance(diagram, SequenceDiagramCanonical):
            return SequenceDiagramCanonical.model_validate(data)
        else:
            return BaseCanonicalDiagram.model_validate(data)

    @classmethod
    def parse_patch_from_response(cls, llm_response: str) -> TargetedRepairPatch:
        """Parse raw LLM JSON response into TargetedRepairPatch."""
        data = CanonicalDiagramParser.parse(llm_response)
        return TargetedRepairPatch.model_validate(data)
