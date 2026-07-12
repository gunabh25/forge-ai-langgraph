import json
import re
from dataclasses import dataclass, field
from typing import List, Set, Any, Dict
from config.logging import get_logger

logger = get_logger("agents.uml_generator.sequence_validator")

@dataclass
class SequenceValidationResult:
    traceable_participants: List[str] = field(default_factory=list)
    non_traceable_participants: List[str] = field(default_factory=list)
    score: int = 100
    approved_registry: List[str] = field(default_factory=list)

    @property
    def is_traceable(self) -> bool:
        return len(self.non_traceable_participants) == 0

class SequenceValidator:
    """Validator for business traceability in Sequence Diagrams."""
    
    def __init__(self):
        # Common technical and generic suffixes to strip for alias resolution
        self.alias_strips = [
            " service", " backend", " system", " management", " api", 
            " processing", " manager", " provider", " database", " db",
            " application", " app", " portal", " interface", " ui",
            " microservice", " engine", " orchestrator"
        ]

    def _normalize_participant_name(self, name: str) -> str:
        """Lightweight alias normalization."""
        # Convert to lowercase and replace underscores/hyphens with spaces
        normalized = name.lower().replace("_", " ").replace("-", " ")
        # Strip extraneous whitespace
        normalized = " ".join(normalized.split())
        
        # Iteratively strip suffixes
        changed = True
        while changed:
            changed = False
            for suffix in self.alias_strips:
                if normalized.endswith(suffix):
                    normalized = normalized[:-len(suffix)].strip()
                    changed = True
                    
        return normalized

    def build_approved_registry(self, plan_json: str) -> Set[str]:
        """Construct the Approved Participant Registry from the Planning JSON."""
        approved = set()
        if not plan_json:
            return approved
            
        try:
            plan = json.loads(plan_json)
            for key in ["actors", "external_systems", "major_components", "major_data_stores"]:
                for item in plan.get(key, []):
                    if isinstance(item, str):
                        approved.add(item)
                    elif isinstance(item, dict) and "name" in item:
                        approved.add(item["name"])
        except json.JSONDecodeError:
            logger.error("Failed to parse diagram plan JSON for approved registry.")
            
        return approved

    def extract_participants_from_puml(self, plantuml_content: str) -> Set[str]:
        """Extract participants from PlantUML syntax."""
        participants = set()
        lines = plantuml_content.splitlines()
        
        # Match explicit declarations like `participant "Name" as alias` or `actor User`
        decl_pattern = re.compile(r'^(?:participant|actor|database|collections|queue|boundary|control|entity|box)\s+(?:"([^"]+)"|(\S+))', re.IGNORECASE)
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("'") or line.startswith("@"):
                continue
                
            decl_match = decl_pattern.search(line)
            if decl_match:
                name = decl_match.group(1) or decl_match.group(2)
                if name:
                    participants.add(name.strip())
                continue
                
            # Naive message matching by splitting
            if "->" in line or "-->" in line:
                # Remove label
                parts = line.split(":", 1)[0]
                # Determine arrow type to split by
                arrow = None
                for a in ["-->>", "-->", "->>", "->"]:
                    if a in parts:
                        arrow = a
                        break
                if arrow:
                    left, right = parts.split(arrow, 1)
                    # Clean up quotes and spaces
                    for p in [left, right]:
                        clean_p = p.strip().strip('"')
                        if clean_p and not clean_p.startswith("["): # ignore boundaries like [ or ]
                            participants.add(clean_p)

        return set(p for p in participants if p)

    def validate(self, plan_json: str, plantuml_content: str) -> SequenceValidationResult:
        """Validate traceability of generated participants against the plan."""
        approved_registry = self.build_approved_registry(plan_json)
        
        # Build normalized lookup map
        normalized_approved = {
            self._normalize_participant_name(p): p for p in approved_registry
        }
        
        generated_participants = self.extract_participants_from_puml(plantuml_content)
        
        traceable = []
        non_traceable = []
        
        logger.debug("Approved Participants:\n%s", list(approved_registry))
        logger.debug("Generated Participants:\n%s", list(generated_participants))
        
        for participant in generated_participants:
            # 1. Exact match
            if participant in approved_registry:
                traceable.append(participant)
                continue
                
            # 2. Alias match
            normalized_participant = self._normalize_participant_name(participant)
            if normalized_participant in normalized_approved:
                logger.debug("Alias Matches:\n'%s' resolved to '%s'", participant, normalized_approved[normalized_participant])
                traceable.append(participant)
                continue
                
            # Non-traceable
            non_traceable.append(participant)
            
        logger.debug("Non Traceable Participants:\n%s", non_traceable)
        
        total = len(generated_participants)
        if total == 0:
            score = 100
        else:
            score = int((len(traceable) / total) * 100)
            
        logger.info("Traceability Score:\n%d / %d participants traceable", len(traceable), total)
        
        return SequenceValidationResult(
            traceable_participants=traceable,
            non_traceable_participants=non_traceable,
            score=score,
            approved_registry=list(approved_registry)
        )
