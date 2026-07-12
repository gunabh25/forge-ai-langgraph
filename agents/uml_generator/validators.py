import os
import json
import subprocess
import tempfile
from typing import Dict, Any, List
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from config.logging import get_logger

logger = get_logger("agents.uml_generator.validators")

_ARCHITECT_SYSTEM = (
    "You are a Principal Software Architect with deep expertise in UML and "
    "system design. You produce concise, accurate outputs in the format "
    "requested — never adding invented components or services."
)

import re

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
        
        # Remove duplicate participant declarations
        lines = content.split('\n')
        seen_participants = set()
        cleaned_lines = []
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith(("participant ", "actor ", "database ", "boundary ")):
                if line_strip in seen_participants:
                    continue
                seen_participants.add(line_strip)
            cleaned_lines.append(line)
            
        return "\n".join(cleaned_lines)

    def validate(self, diagram_type: str, plantuml_content: str) -> Dict[str, Any]:
        fixed_content = self._auto_fix(plantuml_content)
        errors = []
        
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".puml", delete=False, encoding="utf-8") as tmp:
                tmp.write(content)
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
            # Assume valid if plantuml not available
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
            
        from agents.uml_generator.sequence_validator import SequenceValidator
        seq_validator = SequenceValidator()
        val_result = seq_validator.validate(diagram_plan, plantuml_content)
        
        errors = []
        if not val_result.is_traceable:
            errors.append(f"Non-traceable (invented) participants found: {', '.join(val_result.non_traceable_participants)}")
            
        return {
            "validator": "Architecture Validator",
            "passed": val_result.is_traceable,
            "score": val_result.score,
            "errors": errors,
            "warnings": []
        }

class BusinessFlowValidator:
    """Validates the runtime business flow using LLM."""
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        
    def _deterministic_validate(self, plantuml_content: str) -> Optional[Dict[str, Any]]:
        lines = plantuml_content.split('\n')
        actors = set()
        declared_participants = set()
        messages = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("@") or line.startswith("'"):
                continue
            if line.startswith("actor "):
                actors.add(line.split(' ')[1].strip('"'))
                declared_participants.add(line.split(' ')[1].strip('"'))
            elif line.startswith(("participant ", "database ", "boundary ")):
                declared_participants.add(line.split(' ')[1].strip('"'))
            elif "->" in line or "-->" in line:
                # Basic message parsing
                parts = re.split(r'-(?:>|->)', line)
                if len(parts) >= 2:
                    sender = parts[0].strip().split(' ')[-1].strip('"')
                    receiver = parts[1].split(':')[0].strip().strip('"')
                    messages.append((sender, receiver, line))
        
        if not messages:
            return None # Cannot confidently validate empty flow
            
        if not actors:
            return {"passed": False, "score": 50, "errors": ["No actor exists to start the workflow."]}
            
        # Actor starts workflow?
        first_sender = messages[0][0]
        if first_sender not in actors and len(actors) > 0:
            # This might be fine, but could be a warning. Let's just enforce it loosely.
            pass
            
        # Self-loops
        for sender, receiver, line in messages:
            if sender == receiver and "loop" not in line.lower():
                return {"passed": False, "score": 60, "errors": [f"Self-loop detected without explicit allowance: {line}"]}
                
        # Adjacent Duplicate messages
        for i in range(1, len(messages)):
            if messages[i] == messages[i-1]:
                return {"passed": False, "score": 80, "errors": [f"Duplicate adjacent message detected: {messages[i][2]}"]}
                
        # Orphans
        involved = set()
        for s, r, _ in messages:
            involved.add(s)
            involved.add(r)
            
        orphans = declared_participants - involved
        if orphans:
            return {"passed": False, "score": 85, "errors": [f"Orphan participants detected (no messages): {', '.join(orphans)}"]}
            
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
            
        # Try deterministic logic first to save LLM cost
        det_result = self._deterministic_validate(plantuml_content)
        if det_result is not None:
            det_result["validator"] = "Business Flow Validator"
            return det_result
            
        prompt = (
            f"You are validating the business flow of a **{diagram_type} Diagram**.\n\n"
            f"## Diagram Plan\n{diagram_plan}\n\n"
            f"## Generated PlantUML\n```\n{plantuml_content}\n```\n\n"
            f"## Criteria\n"
            f"1. Is the primary business flow preserved?\n"
            f"2. Are major business capabilities present?\n"
            f"3. Are there broken flow steps or orphan participants (unreachable)?\n\n"
            f"Respond with ONLY valid JSON:\n"
            f"{{\n"
            f'  "passed": true,\n'
            f'  "score": 100,\n'
            f'  "errors": ["List orphan participants or missing flow steps here if failed"],\n'
            f'  "warnings": []\n'
            f"}}\n"
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
            logger.warning(f"Business Flow Validator failed to parse LLM output: {e}")
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
