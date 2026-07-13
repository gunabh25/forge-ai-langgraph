import os
import json
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from config.logging import get_logger
import re

from agents.uml_generator.uml_parser import PlantUMLParser, UMLDiagram
from core.business_normalizer import normalize_name

logger = get_logger("agents.uml_generator.validators")

_ARCHITECT_SYSTEM = (
    "You are a Principal Software Architect with deep expertise in UML and "
    "system design. You produce concise, accurate outputs in the format "
    "requested — never adding invented components or services."
)

class GrammarValidator:
    """Validates PlantUML syntax only using local plantuml binary and auto-fixes deterministic issues."""
    
    def _auto_fix(self, content: str) -> str:
        """Automatically repair trivial formatting and duplicate issues."""
        content = content.strip()
        
        if not content.startswith("@startuml"):
            content = "@startuml\n" + content
        if not content.endswith("@enduml"):
            content = content + "\n@enduml"
            
        # Remove empty notes
        content = re.sub(r'note\s+(?:left|right|top|bottom)(?:.*?)\n\s*end note', '', content, flags=re.MULTILINE)
        
        # Remove duplicate participant declarations using canonical aliases
        lines = content.split('\n')
        seen_aliases = set()
        cleaned_lines = []
        
        for line in lines:
            line_strip = line.strip()
            # If it's a declaration, parse it
            if line_strip.startswith(("participant ", "actor ", "database ", "boundary ", "component ", "entity ", "control ", "interface ")):
                parsed = PlantUMLParser._parse_declaration(line_strip)
                if parsed:
                    _, display_name, alias = parsed
                    final_alias = normalize_name(alias if alias else display_name)
                    if final_alias in seen_aliases:
                        continue
                    seen_aliases.add(final_alias)
            cleaned_lines.append(line)
            
        return "\n".join(cleaned_lines)

    def validate(self, diagram_type: str, plantuml_content: str) -> Dict[str, Any]:
        fixed_content = self._auto_fix(plantuml_content)
        errors = []
        
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".puml", delete=False, encoding="utf-8") as tmp:
                tmp.write(fixed_content)
                tmp_path = tmp.name
                
            result = subprocess.run(["plantuml", "-syntax", tmp_path], capture_output=True, text=True, timeout=15)
            os.unlink(tmp_path)
            
            has_error = "Error" in result.stdout or "error" in result.stdout.lower()
            if has_error:
                errors.append(result.stdout.strip())
                return {
                    "validator": "Grammar Validator",
                    "passed": False,
                    "score": 0,
                    "errors": errors,
                    "warnings": []
                }
        except FileNotFoundError:
            pass
        except Exception as exc:
            pass
            
        return {
            "validator": "Grammar Validator",
            "passed": True,
            "score": 100,
            "errors": [],
            "warnings": [],
            "fixed_content": fixed_content
        }

class ArchitectureValidator:
    """Validates architectural consistency (participant traceability)."""
    def validate(self, diagram_type: str, diagram_plan: str, plantuml_content: str) -> Dict[str, Any]:
        if diagram_type.lower() not in ["sequence", "component"]:
            return {
                "validator": "Architecture Validator",
                "passed": True,
                "score": 100,
                "errors": [],
                "warnings": []
            }
            
        from agents.uml_generator.sequence_validator import SequenceValidator, RelationshipValidator
        
        diagram = PlantUMLParser.parse(plantuml_content)
        
        seq_validator = SequenceValidator()
        val_result = seq_validator.validate(diagram_plan, diagram)
        
        rel_validator = RelationshipValidator()
        rel_result = rel_validator.validate(diagram)
        
        errors = []
        if not val_result.is_traceable:
            errors.append(f"Non-traceable (invented) participants found: {', '.join(val_result.non_traceable_participants)}")
            
        if not rel_result.is_valid:
            errors.extend(rel_result.errors)
            
        passed = val_result.is_traceable and rel_result.is_valid
        
        # Calculate composite score
        traceability_score = val_result.score
        rel_score = 100 if rel_result.is_valid else max(0, 100 - len(rel_result.errors) * 10)
        isolated = diagram.isolated_nodes()
        conn_score = 100 if not isolated else max(0, 100 - len(isolated) * 15)
        
        combined_score = int((traceability_score * 0.5) + (rel_score * 0.3) + (conn_score * 0.2))
            
        return {
            "validator": "Architecture Validator",
            "passed": passed,
            "score": combined_score,
            "errors": errors,
            "warnings": [],
            "traceability_metrics": getattr(val_result, "traceability_metrics", {})
        }

class BusinessFlowValidator:
    """Validates the runtime business flow using LLM."""
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        
    def _deterministic_validate(self, diagram: UMLDiagram) -> Optional[Dict[str, Any]]:
        if not diagram.relationships:
            return None # Cannot confidently validate empty flow
            
        actors = [n for n in diagram.business_nodes if n.node_type == "actor"]
        if not actors:
            return {"passed": False, "score": 50, "errors": ["No actor exists to start the workflow."]}
            
        # Self-loops
        for r in diagram.relationships:
            s_node = diagram.resolve(r.source)
            t_node = diagram.resolve(r.target)
            if s_node and t_node and s_node == t_node:
                return {"passed": False, "score": 60, "errors": [f"Self-loop detected on: {s_node.display_name}"]}
                
        # Adjacent Duplicate messages
        rels = diagram.relationships
        for i in range(1, len(rels)):
            prev = rels[i-1]
            curr = rels[i]
            if prev.source == curr.source and prev.target == curr.target and prev.label == curr.label:
                return {"passed": False, "score": 80, "errors": [f"Duplicate adjacent message detected: {curr.source} -> {curr.target}"]}
                
        # Orphans
        orphans = diagram.isolated_nodes()
        if orphans:
            orphan_names = [o.display_name for o in orphans]
            return {"passed": False, "score": 85, "errors": [f"Orphan participants detected (no messages): {', '.join(orphan_names)}"]}
            
        return {"passed": True, "score": 100, "errors": [], "warnings": []}

    def validate(self, diagram_type: str, diagram_plan: str, plantuml_content: str) -> Dict[str, Any]:
        if diagram_type.lower() not in ["sequence", "activity"]:
            return {
                "validator": "Business Flow Validator",
                "passed": True,
                "score": 100,
                "errors": [],
                "warnings": []
            }
            
        diagram = PlantUMLParser.parse(plantuml_content)
        det_result = self._deterministic_validate(diagram)
        if det_result is not None:
            det_result["validator"] = "Business Flow Validator"
            return det_result
            
        prompt = (
            f"You are validating the business flow of a **{diagram_type} Diagram**.\\n\\n"
            f"## Diagram Plan\\n{diagram_plan}\\n\\n"
            f"## Generated PlantUML\\n```\\n{plantuml_content}\\n```\\n\\n"
            f"## Criteria\\n"
            f"1. Is the primary business flow preserved?\\n"
            f"2. Are major business capabilities present?\\n"
            f"3. Are there broken flow steps or orphan participants (unreachable)?\\n\\n"
            f"Respond with ONLY valid JSON:\\n"
            f"{{\\n"
            f'  "passed": true,\\n'
            f'  "score": 100,\\n'
            f'  "errors": ["List orphan participants or missing flow steps here if failed"],\\n'
            f'  "warnings": []\\n'
            f"}}\\n"
        )
        
        try:
            response = self.llm.invoke([SystemMessage(content=_ARCHITECT_SYSTEM), HumanMessage(content=prompt)])
            raw = str(response.content).replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            return {
                "validator": "Business Flow Validator",
                "passed": result.get("passed", True),
                "score": result.get("score", 100),
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", [])
            }
        except Exception as e:
            logger.warning("Business Flow Validator failed to parse LLM output: %s", e)
            return {
                "validator": "Business Flow Validator",
                "passed": True,
                "score": 100,
                "errors": [],
                "warnings": []
            }

class ReviewValidator:
    """Evaluates diagram readability, abstraction, and quality."""
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        
    def validate(self, diagram_type: str, plantuml_content: str, constraints: Dict[str, Any], min_score: int) -> Dict[str, Any]:
        constraint_lines = "\n".join(f"- {k.replace('_', ' ')}: {v}" for k, v in constraints.items()) or "No constraints."
        
        review_prompt = (
            f"You are reviewing a generated **{diagram_type} Diagram** (PlantUML) for architecture-review quality.\n\n"
            f"## Constraints\n{constraint_lines}\n\n"
            f"## Generated PlantUML\n```\n{plantuml_content}\n```\n\n"
            f"## Review Criteria (Score out of 100)\n"
            f"Evaluate based on Readability, Abstraction, Diagram Quality, Naming, and Visual Complexity.\n\n"
            f"Respond with ONLY valid JSON:\n"
            f"{{\n"
            f'  "score": 95,\n'
            f'  "errors": ["Specific issues affecting readability or quality"],\n'
            f'  "warnings": []\n'
            f"}}\n"
        )
        
        try:
            response = self.llm.invoke([SystemMessage(content=_ARCHITECT_SYSTEM), HumanMessage(content=review_prompt)])
            raw = str(response.content).replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            score = result.get("score", 100)
            # Normalizing score from old out-of-10 to out-of-100 logic just in case the LLM outputs <=10
            if score <= 10:
                score *= 10
            passed = score >= min_score * 10 if min_score <= 10 else score >= min_score
            return {
                "validator": "Review Agent",
                "passed": passed,
                "score": score,
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", [])
            }
        except Exception as e:
            logger.warning(f"Review Validator failed to parse LLM output: {e}")
            return {
                "validator": "Review Agent",
                "passed": True,
                "score": 100,
                "errors": [],
                "warnings": []
            }

class ValidationPipeline:
    """Reusable validation pipeline combining Grammar, Architecture, and Business Flow validators."""
    
    def __init__(self, llm: BaseChatModel):
        self.grammar_val = GrammarValidator()
        self.arch_val = ArchitectureValidator()
        self.flow_val = BusinessFlowValidator(llm)
        self.llm = llm

    def validate_diagram(self, diagram_type: str, diagram_plan: str, plantuml_content: str) -> Dict[str, Any]:
        """
        Runs all validators sequentially.
        Returns a dict containing validation feedback, status fields, and optionally fixed_content.
        """
        pipeline_feedback = None
        uml_validation_metrics = {}
        syntax_valid = False
        
        # Layer 1: Grammar Validator (Local, No LLM, auto-fixes)
        grammar_res = self.grammar_val.validate(diagram_type, plantuml_content)
        if "fixed_content" in grammar_res:
            plantuml_content = grammar_res["fixed_content"]
        
        uml_validation_metrics["grammar_score"] = grammar_res["score"]
        grammar_status = "passed" if grammar_res["passed"] else "failed"
        
        if not grammar_res["passed"]:
            pipeline_feedback = grammar_res
            syntax_valid = False
            return {
                "pipeline_feedback": pipeline_feedback,
                "uml_validation_metrics": uml_validation_metrics,
                "syntax_valid": syntax_valid,
                "fixed_content": plantuml_content,
                "grammar_status": grammar_status,
                "architecture_status": "skipped",
                "business_flow_status": "skipped"
            }
            
        syntax_valid = True
        
        # Layer 2: Architecture Validator
        arch_res = self.arch_val.validate(diagram_type, diagram_plan, plantuml_content)
        uml_validation_metrics["architecture_score"] = arch_res["score"]
        architecture_status = "passed" if arch_res["passed"] else "failed"
        
        if not arch_res["passed"]:
            pipeline_feedback = arch_res
            return {
                "pipeline_feedback": pipeline_feedback,
                "uml_validation_metrics": uml_validation_metrics,
                "syntax_valid": syntax_valid,
                "fixed_content": plantuml_content,
                "grammar_status": grammar_status,
                "architecture_status": architecture_status,
                "business_flow_status": "skipped"
            }
            
        # Layer 3: Business Flow Validator
        flow_res = self.flow_val.validate(diagram_type, diagram_plan, plantuml_content)
        uml_validation_metrics["business_flow_score"] = flow_res["score"]
        business_flow_status = "passed" if flow_res["passed"] else "failed"
        
        if not flow_res["passed"]:
            pipeline_feedback = flow_res
            
        return {
            "pipeline_feedback": pipeline_feedback,
            "uml_validation_metrics": uml_validation_metrics,
            "syntax_valid": syntax_valid,
            "fixed_content": plantuml_content,
            "grammar_status": grammar_status,
            "architecture_status": architecture_status,
            "business_flow_status": business_flow_status,
            "llm_invoked": flow_res.get("llm_invoked", False)
        }
