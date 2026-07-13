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
    
    ARROW_PATTERN = re.compile(r'([-=.]+(?:left|right|up|down)?[-=.]*(?:>|>>|o|x)?|<[-=.]+(?:left|right|up|down)?[-=.]*(?:>|>>|o|x)?|[-=.]+|o[-=.]+>|x[-=.]+>)')

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
    def _parse_declaration(cls, line: str) -> Optional[Tuple[str, str, str]]:
        clean_line = re.sub(r'<<[^>]+>>', '', line).strip()
        if not clean_line:
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
        in_quotes = False
        arrow_match = None
        for m in cls.ARROW_PATTERN.finditer(line):
            before = line[:m.start()]
            if before.count('"') % 2 == 0:
                arrow_match = m
                break
                
        if not arrow_match:
            return None
            
        source_str = line[:arrow_match.start()].strip()
        rest = line[arrow_match.end():].strip()
        
        target_str = rest
        label = None
        if ':' in rest:
            parts = rest.split(':', 1)
            target_str = parts[0].strip()
            label = parts[1].strip()
            
        source = source_str.strip('"')
        target = target_str.strip('"')
        
        if not source or not target:
            return None
            
        arrow_type = cls._parse_arrow_type(arrow_match.group(0))
        
        return UMLRelationship(source=source, target=target, arrow_type=arrow_type, label=label)

    @classmethod
    def parse(cls, plantuml_content: str) -> UMLDiagram:
        diagram = UMLDiagram()
        lines = plantuml_content.split('\n')
        seen_aliases = set()
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("'") or line.startswith("@"):
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
            if not line or line.startswith("'") or line.startswith("@"):
                continue
                
            if cls._parse_declaration(line):
                continue
                
            rel = cls._parse_relationship(line)
            if rel:
                diagram.relationships.append(rel)
                
        return diagram
