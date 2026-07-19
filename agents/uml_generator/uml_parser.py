import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Set
from enum import Enum, auto
from core.business_normalizer import normalize_name

logger = logging.getLogger("agents.uml_generator.uml_parser")

class ArrowType(Enum):
    SYNC = auto()
    ASYNC = auto()
    RETURN = auto()
    DOTTED = auto()
    COMPOSITION = auto()
    AGGREGATION = auto()
    UNKNOWN = auto()

@dataclass
class UMLNode:
    display_name: str
    alias: str
    node_type: str
    
    @property
    def normalized_name(self) -> str:
        return normalize_name(self.display_name)

@dataclass
class UMLRelationship:
    source: str
    target: str
    arrow_type: ArrowType
    label: Optional[str] = None

class UMLDiagram:
    def __init__(self):
        self.nodes: List[UMLNode] = []
        self.relationships: List[UMLRelationship] = []
        
    def to_plantuml(self) -> str:
        lines = ["@startuml"]
        
        # Serialize nodes
        for node in self.nodes:
            alias_part = f' as {node.alias}' if node.alias and node.alias != node.display_name else ''
            # Quote display name if it has spaces or special chars
            if not node.display_name.isalnum():
                lines.append(f'{node.node_type} "{node.display_name}"{alias_part}')
            else:
                lines.append(f'{node.node_type} {node.display_name}{alias_part}')
                
        # Serialize relationships
        for rel in self.relationships:
            arrow = "->"
            if rel.arrow_type == ArrowType.ASYNC: arrow = ">>"
            elif rel.arrow_type == ArrowType.RETURN: arrow = "-->"
            elif rel.arrow_type == ArrowType.DOTTED: arrow = "..>"
            elif rel.arrow_type == ArrowType.COMPOSITION: arrow = "*--"
            elif rel.arrow_type == ArrowType.AGGREGATION: arrow = "o--"
            
            label_part = f" : {rel.label}" if rel.label else ""
            lines.append(f'"{rel.source}" {arrow} "{rel.target}"{label_part}')
            
        lines.append("@enduml")
        return "\n".join(lines)
        
    @property
    def business_nodes(self) -> List[UMLNode]:
        return [n for n in self.nodes if n.node_type in PlantUMLParser.BUSINESS_NODES]
        
    @property
    def layout_nodes(self) -> List[UMLNode]:
        return [n for n in self.nodes if n.node_type in PlantUMLParser.LAYOUT_NODES]

    @property
    def alias_map(self) -> Dict[str, UMLNode]:
        return {n.alias: n for n in self.nodes}

    def get_node(self, name: str) -> Optional[UMLNode]:
        if name in self.alias_map:
            return self.alias_map[name]
        for n in self.nodes:
            if n.display_name == name:
                return n
        return None

    def resolve(self, name: str) -> Optional[UMLNode]:
        return self.get_node(name)

    def outgoing(self, node: UMLNode) -> List[UMLRelationship]:
        return [r for r in self.relationships if self.resolve(r.source) == node]

    def incoming(self, node: UMLNode) -> List[UMLRelationship]:
        return [r for r in self.relationships if self.resolve(r.target) == node]

    def neighbors(self, node: UMLNode) -> List[UMLNode]:
        res = set()
        for r in self.outgoing(node):
            if t := self.resolve(r.target):
                res.add(t)
        for r in self.incoming(node):
            if s := self.resolve(r.source):
                res.add(s)
        return list(res)

    def isolated_nodes(self) -> List[UMLNode]:
        isolated = []
        for n in self.business_nodes:
            if not self.outgoing(n) and not self.incoming(n):
                isolated.append(n)
        return isolated

    def duplicate_edges(self) -> List[UMLRelationship]:
        seen = set()
        duplicates = []
        for r in self.relationships:
            s_node = self.resolve(r.source)
            t_node = self.resolve(r.target)
            if not s_node or not t_node:
                continue
            edge = (s_node.normalized_name, t_node.normalized_name, r.label)
            if edge in seen:
                duplicates.append(r)
            else:
                seen.add(edge)
        return duplicates

    def root_nodes(self) -> List[UMLNode]:
        roots = []
        for n in self.business_nodes:
            if not self.incoming(n) and self.outgoing(n):
                roots.append(n)
        return roots

    def leaf_nodes(self) -> List[UMLNode]:
        leaves = []
        for n in self.business_nodes:
            if not self.outgoing(n) and self.incoming(n):
                leaves.append(n)
        return leaves

    def connected_components(self) -> List[Set[UMLNode]]:
        visited = set()
        components = []
        b_nodes = set(self.business_nodes)
        
        for node in b_nodes:
            if node not in visited:
                comp = set()
                queue = [node]
                while queue:
                    curr = queue.pop(0)
                    if curr not in visited:
                        visited.add(curr)
                        comp.add(curr)
                        for nbr in self.neighbors(curr):
                            if nbr in b_nodes and nbr not in visited:
                                queue.append(nbr)
                components.append(comp)
        return components

    def has_cycle(self) -> bool:
        visited = set()
        rec_stack = set()
        b_nodes = self.business_nodes
        
        def visit(n: UMLNode) -> bool:
            visited.add(n)
            rec_stack.add(n)
            for r in self.outgoing(n):
                if t := self.resolve(r.target):
                    if t in b_nodes:
                        if t not in visited:
                            if visit(t):
                                return True
                        elif t in rec_stack:
                            return True
            rec_stack.remove(n)
            return False

        for node in b_nodes:
            if node not in visited:
                if visit(node):
                    return True
        return False

class PlantUMLParser:
    """Lightweight deterministic parser for PlantUML diagrams."""
    
    BUSINESS_NODES = {
        'actor', 'participant', 'component', 'database', 'entity', 
        'boundary', 'control', 'interface', 'external_system', 'usecase', 'card'
    }
    
    LAYOUT_NODES = {
        'package', 'frame', 'folder', 'cloud', 'rectangle', 'node', 'collections', 'queue', 'storage', 'artifact'
    }

    DIRECTIVE_PREFIXES = (
        "title", "header", "footer", "skinparam", "top to bottom", "left to right",
        "direction", "hide", "show", "remove", "scale", "page", "legend", "end legend",
        "note", "end note"
    )
    
    ARROW_PATTERN = re.compile(
        r'(\*?o?<?[-=.]+(?:\[[^\]]*\])?(?:left|right|up|down|h|v)?[-=.]*(?:>|>>|o|x|\*)?)'
    )

    @classmethod
    def _parse_arrow_type(cls, arrow_str: str) -> ArrowType:
        if '..' in arrow_str:
            return ArrowType.DOTTED
        elif '-->' in arrow_str or '<--' in arrow_str:
            return ArrowType.RETURN
        elif '->' in arrow_str or '<-' in arrow_str:
            return ArrowType.SYNC
        elif '>>' in arrow_str or '<<' in arrow_str:
            return ArrowType.ASYNC
        elif '*--' in arrow_str or '--*' in arrow_str:
            return ArrowType.COMPOSITION
        elif 'o--' in arrow_str or '--o' in arrow_str:
            return ArrowType.AGGREGATION
        return ArrowType.UNKNOWN

    @classmethod
    def _is_directive(cls, line: str) -> bool:
        clean = line.strip()
        if not clean or clean.startswith("'") or clean.startswith("@") or clean in ("{", "}"):
            return True
        lower_clean = clean.lower()
        for prefix in cls.DIRECTIVE_PREFIXES:
            if lower_clean.startswith(prefix):
                return True
        return False

    @classmethod
    def _parse_declaration(cls, line: str) -> Optional[Tuple[str, str, Optional[str]]]:
        clean_line = re.sub(r'<<[^>]+>>', '', line).strip()
        if clean_line.endswith('{'):
            clean_line = clean_line[:-1].strip()
        if not clean_line or cls._is_directive(clean_line):
            return None
            
        node_type = None
        display_name = None
        alias = None
        
        if clean_line.startswith('['):
            close_idx = clean_line.find(']')
            if close_idx != -1:
                display_name = clean_line[1:close_idx].strip()
                node_type = "component"
                rest = clean_line[close_idx+1:].strip()
                if rest.lower().startswith("as "):
                    alias = rest[3:].strip()
                return node_type, display_name, alias
                
        if clean_line.startswith('()'):
            node_type = "usecase"
            rest = clean_line[2:].strip()
        else:
            match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s+(.*)$', clean_line)
            if not match:
                return None
            node_type = match.group(1).lower()
            if node_type not in cls.BUSINESS_NODES and node_type not in cls.LAYOUT_NODES:
                return None
            rest = match.group(2).strip()

        if rest.startswith('"'):
            end_quote = rest.find('"', 1)
            if end_quote != -1:
                display_name = rest[1:end_quote].strip()
                rest = rest[end_quote+1:].strip()
                if rest.lower().startswith("as "):
                    alias = rest[3:].strip()
            else:
                display_name = rest[1:].strip()
        else:
            parts = re.split(r'\s+as\s+', rest, maxsplit=1, flags=re.IGNORECASE)
            display_name = parts[0].strip()
            if len(parts) > 1:
                alias = parts[1].strip()
                
        if display_name:
            return node_type, display_name, alias
        return None

    @classmethod
    def _parse_relationship(cls, line: str) -> Optional[UMLRelationship]:
        clean_line = line.strip()
        if cls._is_directive(clean_line):
            return None

        arrow_match = None
        for m in cls.ARROW_PATTERN.finditer(clean_line):
            before = clean_line[:m.start()]
            if before.count('"') % 2 == 0:
                arrow_match = m
                break
                
        if not arrow_match:
            return None
            
        source_str = clean_line[:arrow_match.start()].strip()
        rest = clean_line[arrow_match.end():].strip()
        
        label = None
        inline_label_match = re.match(r'^"([^"]*)"\s*([-=.]*(?:>|>>|o|x)?)(.*)', rest)
        if inline_label_match and inline_label_match.group(2):
            label = inline_label_match.group(1).strip()
            arrow_end = inline_label_match.group(2)
            rest = inline_label_match.group(3).strip()
            arrow_str = arrow_match.group(0) + arrow_end
        else:
            arrow_str = arrow_match.group(0)
            
        target_str = rest
        if ':' in rest:
            parts = rest.split(':', 1)
            target_str = parts[0].strip()
            trailing_label = parts[1].strip()
            if trailing_label:
                label = trailing_label
            
        source = source_str.strip('" ')
        target = target_str.strip('" ')

        source = re.split(cls.ARROW_PATTERN, source)[0].strip()
        target = re.split(cls.ARROW_PATTERN, target)[0].strip()

        source = re.sub(r'^(?:left|right|up|down)\s+', '', source, flags=re.IGNORECASE).strip()
        target = re.sub(r'^(?:left|right|up|down)\s+', '', target, flags=re.IGNORECASE).strip()
        
        if not source or not target:
            return None
            
        arrow_type = cls._parse_arrow_type(arrow_str)
        
        return UMLRelationship(source=source, target=target, arrow_type=arrow_type, label=label)

    @classmethod
    def parse(cls, plantuml_content: str) -> UMLDiagram:
        diagram = UMLDiagram()
        lines = plantuml_content.split('\n')
        seen_aliases = set()
        
        for line in lines:
            line = line.strip()
            if not line or cls._is_directive(line):
                continue
                
            parsed = cls._parse_declaration(line)
            if parsed:
                node_type, display_name, alias = parsed
                final_alias = alias if alias else display_name
                
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "--------------------------------\n"
                        "Node Parsed\n"
                        "Type: %s\n"
                        "Display Name: %s\n"
                        "Alias: %s\n"
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
                    
        for line in lines:
            line = line.strip()
            if not line or cls._is_directive(line):
                continue
                
            if cls._parse_declaration(line):
                continue
                
            rel = cls._parse_relationship(line)
            if rel:
                diagram.relationships.append(rel)
                
        return diagram
