import re
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class UMLNode:
    display_name: str
    alias: str
    node_type: str

@dataclass
class UMLRelationship:
    source: str
    target: str
    label: Optional[str] = None

@dataclass
class UMLDiagram:
    nodes: List[UMLNode] = field(default_factory=list)
    relationships: List[UMLRelationship] = field(default_factory=list)

class PlantUMLParser:
    """Lightweight deterministic parser for PlantUML diagrams."""
    
    # Matches: type "display name" <<stereotype>> as alias
    # e.g., component "Claim Submission" <<service>> as ClaimSubmission
    # or actor "Customer" as Customer
    # or database ClaimsDB
    DECLARATION_PATTERN = re.compile(
        r'^(participant|actor|component|database|collections|queue|boundary|control|entity|node|cloud)\s+'
        r'(?:(?:"([^"]+)")|(\S+))'            # Group 2: quoted name, Group 3: unquoted name
        r'(?:\s+<<[^>]+>>)?'                 # Optional stereotype
        r'(?:\s+as\s+(\S+))?',               # Group 4: alias
        re.IGNORECASE
    )
    
    RELATIONSHIP_PATTERN = re.compile(
        r'^([a-zA-Z0-9_.-]+)\s*(?:[-=.]+(?:left|right|up|down)?[-=.]*>|<[-=.]+(?:left|right|up|down)?[-=.]+|[-=.]+)\s*([a-zA-Z0-9_.-]+)(?:\s*:\s*(.*))?$'
    )

    @classmethod
    def parse(cls, plantuml_content: str) -> UMLDiagram:
        diagram = UMLDiagram()
        lines = plantuml_content.split('\n')
        
        seen_aliases = set()
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("'") or line.startswith("@") or line.startswith("note "):
                continue
                
            decl_match = cls.DECLARATION_PATTERN.match(line)
            if decl_match:
                node_type = decl_match.group(1).lower()
                quoted_name = decl_match.group(2)
                unquoted_name = decl_match.group(3)
                alias = decl_match.group(4)
                
                display_name = quoted_name if quoted_name else unquoted_name
                final_alias = alias if alias else display_name
                
                if final_alias not in seen_aliases:
                    diagram.nodes.append(UMLNode(
                        display_name=display_name.strip(),
                        alias=final_alias.strip(),
                        node_type=node_type
                    ))
                    seen_aliases.add(final_alias)
                continue
                
            # Fallback relationship naive parsing if strict relationship pattern doesn't match
            # But let's try the strict one first
            rel_match = cls.RELATIONSHIP_PATTERN.match(line)
            if rel_match:
                source = rel_match.group(1).strip()
                target = rel_match.group(2).strip()
                label = rel_match.group(3).strip() if rel_match.group(3) else None
                
                diagram.relationships.append(UMLRelationship(
                    source=source,
                    target=target,
                    label=label
                ))
                
                # Auto-register implicitly declared nodes (often used in simple diagrams)
                for node_alias in [source, target]:
                    if node_alias not in seen_aliases:
                        diagram.nodes.append(UMLNode(
                            display_name=node_alias,
                            alias=node_alias,
                            node_type="unknown"
                        ))
                        seen_aliases.add(node_alias)

        return diagram
