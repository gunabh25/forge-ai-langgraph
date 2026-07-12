import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger("agents.uml_generator.uml_parser")

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
    
    RELATIONSHIP_PATTERN = re.compile(
        r'^(?:"([^"]+)"|([a-zA-Z0-9_.-]+))'                                        # Group 1: Quoted Source, Group 2: Unquoted Source
        r'\s*(?:(?:<|<<|o|x)?[-=.]+(?:left|right|up|down)?[-=.]*(?:>|>>|o|x)?)\s*' # The arrow
        r'(?:"([^"]+)"|([a-zA-Z0-9_.-]+))'                                        # Group 3: Quoted Target, Group 4: Unquoted Target
        r'(?:\s*:\s*(.*))?$'                                                       # Group 5: Label
    )

    # Keywords that start a line but are NOT entities
    NON_ENTITY_KEYWORDS = {
        'note', 'skinparam', 'title', 'return', 'autonumber', 'hide', 'show', 
        'activate', 'deactivate', 'group', 'loop', 'alt', 'else', 'opt', 
        'par', 'break', 'critical', 'box', 'end', 'scale', 'legend', 
        'header', 'footer', 'newpage', 'title', 'caption'
    }

    @classmethod
    def _parse_declaration(cls, line: str) -> Optional[Tuple[str, str, Optional[str]]]:
        """
        Parses a declaration line and returns (node_type, display_name, alias).
        Returns None if the line is not a declaration.
        """
        # Remove stereotypes << ... >> for simpler parsing
        clean_line = re.sub(r'<<[^>]+>>', '', line).strip()
        if not clean_line:
            return None
            
        node_type = None
        display_name = None
        alias = None
        
        # 1. Check for shorthand bracket syntax for components: [Display Name] as Alias
        if clean_line.startswith('['):
            close_idx = clean_line.find(']')
            if close_idx != -1:
                display_name = clean_line[1:close_idx].strip()
                node_type = "component"
                rest = clean_line[close_idx+1:].strip()
                if rest.lower().startswith("as "):
                    alias = rest[3:].strip()
                return node_type, display_name, alias
                
        # 2. Check for shorthand parentheses syntax for usecases: () "Display Name" as Alias
        if clean_line.startswith('()'):
            node_type = "usecase"
            rest = clean_line[2:].strip()
        else:
            # Standard type declaration: TYPE "Display Name" as Alias
            match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s+(.*)$', clean_line)
            if not match:
                return None
            node_type = match.group(1).lower()
            if node_type in cls.NON_ENTITY_KEYWORDS:
                return None
            rest = match.group(2).strip()

        # Parse the rest: "Display Name" as Alias OR DisplayName as Alias
        if rest.startswith('"'):
            end_quote = rest.find('"', 1)
            if end_quote != -1:
                display_name = rest[1:end_quote].strip()
                rest = rest[end_quote+1:].strip()
                if rest.lower().startswith("as "):
                    alias = rest[3:].strip()
            else:
                # Missing end quote, fallback
                display_name = rest[1:].strip()
        else:
            # Unquoted name
            parts = re.split(r'\s+as\s+', rest, maxsplit=1, flags=re.IGNORECASE)
            display_name = parts[0].strip()
            if len(parts) > 1:
                alias = parts[1].strip()
                
        if display_name:
            return node_type, display_name, alias
        return None

    @classmethod
    def parse(cls, plantuml_content: str) -> UMLDiagram:
        diagram = UMLDiagram()
        lines = plantuml_content.split('\n')
        
        seen_aliases = set()
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("'") or line.startswith("@"):
                continue
                
            # 1. Check for Relationship first (to avoid parsing arrows as declarations)
            rel_match = cls.RELATIONSHIP_PATTERN.match(line)
            if rel_match:
                source = rel_match.group(1) if rel_match.group(1) else rel_match.group(2)
                target = rel_match.group(3) if rel_match.group(3) else rel_match.group(4)
                label = rel_match.group(5).strip() if rel_match.group(5) else None
                
                diagram.relationships.append(UMLRelationship(
                    source=source,
                    target=target,
                    label=label
                ))
                continue
                
            # 2. Check for node declaration
            parsed = cls._parse_declaration(line)
            if parsed:
                node_type, display_name, alias = parsed
                final_alias = alias if alias else display_name
                
                # Log the parsed node deterministically
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "--------------------------------\n"
                        "Node Parsed\n"
                        "Type\n%s\n"
                        "Display Name\n%s\n"
                        "Alias\n%s\n"
                        "--------------------------------",
                        node_type, display_name, final_alias
                    )
                
                if final_alias not in seen_aliases:
                    diagram.nodes.append(UMLNode(
                        display_name=display_name,
                        alias=final_alias,
                        node_type=node_type
                    ))
                    seen_aliases.add(final_alias)
                continue

        return diagram
