import json
from dataclasses import dataclass, field
from typing import List, Set, Any, Dict
from config.logging import get_logger

from agents.uml_generator.uml_parser import UMLDiagram
from core.business_normalizer import normalize_components, normalize_name

logger = get_logger("agents.uml_generator.sequence_validator")

@dataclass
class SequenceValidationResult:
    traceable_participants: List[str] = field(default_factory=list)
    non_traceable_participants: List[str] = field(default_factory=list)
    score: int = 100
    approved_registry: List[str] = field(default_factory=list)
    traceability_metrics: Dict[str, Any] = field(default_factory=dict)
    participant_details: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_traceable(self) -> bool:
        return len(self.non_traceable_participants) == 0

from agents.uml_generator.canonical_parser import CanonicalDiagramParser, CanonicalParseError


class SequenceValidator:
    """Validator for business traceability in Sequence and Component Diagrams."""
    
    def __init__(self):
        self.alias_strips = [
            " service", " backend", " system", " management", " api", 
            " processing", " manager", " provider", " database", " db",
            " application", " app", " portal", " interface", " ui",
            " microservice", " engine", " orchestrator"
        ]

    def build_approved_registry(self, plan_json: str) -> Set[str]:
        """Construct the Approved Participant Registry from the Planning JSON."""
        approved = set()
        if not plan_json:
            return approved
            
        try:
            plan = CanonicalDiagramParser.parse(plan_json)
            for key in ["actors", "external_systems", "major_components", "major_data_stores"]:
                for item in plan.get(key, []):
                    if isinstance(item, str):
                        approved.add(item)
                    elif isinstance(item, dict) and "name" in item:
                        approved.add(item["name"])
        except (CanonicalParseError, json.JSONDecodeError, TypeError):
            logger.error("Failed to parse diagram plan JSON for approved registry.")
            
        return approved

    def _get_synonym_match(self, normalized_name: str, normalized_approved: Dict[str, str]) -> str:
        changed = True
        current_name = normalized_name
        while changed:
            changed = False
            for suffix in self.alias_strips:
                if current_name.endswith(suffix):
                    current_name = current_name[:-len(suffix)].strip()
                    changed = True
                    
        for app_norm, original in normalized_approved.items():
            app_current = app_norm
            changed = True
            while changed:
                changed = False
                for suffix in self.alias_strips:
                    if app_current.endswith(suffix):
                        app_current = app_current[:-len(suffix)].strip()
                        changed = True
            if current_name == app_current and current_name:
                return original
                
        return ""

    def validate(self, plan_json: str, uml_diagram: UMLDiagram) -> SequenceValidationResult:
        """Validate traceability of generated participants against the plan."""
        approved_registry = self.build_approved_registry(plan_json)
        
        normalized_approved = {
            normalize_name(p): p for p in approved_registry
        }
        
        traceable = []
        non_traceable = []
        participant_details = []
        
        # Only evaluate traceability on Business Nodes (Layout Nodes are skipped)
        business_nodes = uml_diagram.business_nodes
        
        metrics = {
            "planned_components": len(approved_registry),
            "generated_components": len(business_nodes),
            "exact_matches": 0,
            "alias_matches": 0,
            "normalizer_matches": 0,
            "failed_matches": 0,
            "traceability_score": 100
        }
        
        logger.debug("Approved Participants:\n%s", list(approved_registry))
        
        for node in business_nodes:
            display_name = node.display_name
            normalized = node.normalized_name
            
            detail = {
                "traceable": False,
                "display_name": display_name,
                "normalized_name": normalized,
                "planning_match": None,
                "match_type": "None"
            }
            
            if normalized in normalized_approved:
                detail["traceable"] = True
                detail["planning_match"] = normalized_approved[normalized]
                detail["match_type"] = "Exact"
                traceable.append(display_name)
                metrics["exact_matches"] += 1
            else:
                normalized_business = normalize_components([display_name])
                if normalized_business and normalize_name(normalized_business[0]) in normalized_approved:
                    matched_val = normalized_approved[normalize_name(normalized_business[0])]
                    detail["traceable"] = True
                    detail["planning_match"] = matched_val
                    detail["match_type"] = "Business Normalizer"
                    traceable.append(display_name)
                    metrics["normalizer_matches"] += 1
                else:
                    synonym_match = self._get_synonym_match(normalized, normalized_approved)
                    if synonym_match:
                        detail["traceable"] = True
                        detail["planning_match"] = synonym_match
                        detail["match_type"] = "Synonym"
                        traceable.append(display_name)
                        metrics["alias_matches"] += 1
                    else:
                        detail["traceable"] = False
                        non_traceable.append(display_name)
                        metrics["failed_matches"] += 1
            
            logger.debug("Traceability Result:\n------------------------------------------------\n"
                        f"Display Name: {detail['display_name']}\n"
                        f"↓\nNormalized: {detail['normalized_name']}\n"
                        f"↓\nPlanning Match: {detail['planning_match']}\n"
                        f"↓\nMatch Type: {detail['match_type']}\n"
                        f"↓\nResult: {'TRACEABLE' if detail['traceable'] else 'NON_TRACEABLE'}\n"
                        "------------------------------------------------")
            participant_details.append(detail)
            
        total = len(business_nodes)
        if total == 0:
            score = 100
        else:
            score = int((len(traceable) / total) * 100)
            
        metrics["traceability_score"] = score
            
        logger.debug("Traceability Score:\n%d / %d participants traceable", len(traceable), total)
        
        return SequenceValidationResult(
            traceable_participants=traceable,
            non_traceable_participants=non_traceable,
            score=score,
            approved_registry=list(approved_registry),
            traceability_metrics=metrics,
            participant_details=participant_details
        )

@dataclass
class RelationshipValidationResult:
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)

class RelationshipValidator:
    """Validates structural correctness of UML relationships."""
    
    def validate(self, diagram: UMLDiagram) -> RelationshipValidationResult:
        errors = []
        seen_edges = set()
        
        for rel in diagram.relationships:
            src_node = diagram.resolve(rel.source)
            tgt_node = diagram.resolve(rel.target)
            
            if not src_node:
                errors.append(f"Graph Error: Source node '{rel.source}' is used in a relationship but was never declared. (Dangling alias)")
            
            if not tgt_node:
                errors.append(f"Graph Error: Target node '{rel.target}' is used in a relationship but was never declared. (Dangling alias)")
                
            if src_node and tgt_node and src_node.normalized_name == tgt_node.normalized_name:
                errors.append(f"Graph Error: Self-loop detected on '{src_node.display_name}'.")
                
            if src_node and tgt_node:
                edge = (src_node.normalized_name, tgt_node.normalized_name)
                if edge in seen_edges:
                    errors.append(f"Graph Error: Duplicate relationship detected from '{src_node.display_name}' to '{tgt_node.display_name}'. Combine multiple messages into a single labeled edge or remove duplicates.")
                seen_edges.add(edge)
            
        isolated = diagram.isolated_nodes()
        for iso in isolated:
            errors.append(f"Graph Error: Isolated business node detected '{iso.display_name}'. Nodes must participate in at least one relationship.")
            
        return RelationshipValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
