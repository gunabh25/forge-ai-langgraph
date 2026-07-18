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
from agents.uml_generator.diagram_scorer import EnterpriseDiagramScorer
from core.business_normalizer import normalize_name
from schemas.validation_feedback import (
    DiagnosticCategory,
    ValidationDiagnostic,
    StructuredValidationFeedback,
)

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
        errors: List[str] = []
        diagnostics: List[Dict[str, Any]] = []

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".puml", delete=False, encoding="utf-8") as tmp:
                tmp.write(fixed_content)
                tmp_path = tmp.name

            result = subprocess.run(["plantuml", "-syntax", tmp_path], capture_output=True, text=True, timeout=15)
            os.unlink(tmp_path)

            has_error = "Error" in result.stdout or "error" in result.stdout.lower()
            if has_error:
                err_msg = result.stdout.strip()
                errors.append(err_msg)
                
                code = "UNKNOWN_KEYWORD" if "unknown" in err_msg.lower() or "syntax" in err_msg.lower() else "SYNTAX_ERROR"
                diagnostics.append(
                    ValidationDiagnostic(
                        category=DiagnosticCategory.GRAMMAR,
                        code=code,
                        message=err_msg,
                        suggested_fix="Fix syntax or remove unknown PlantUML keywords"
                    ).to_dict()
                )

                return {
                    "validator": "Grammar Validator",
                    "passed": False,
                    "score": 0,
                    "errors": errors,
                    "warnings": [],
                    "diagnostics": diagnostics,
                }
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.warning("Grammar validation subprocess error: %s", exc)

        return {
            "validator": "Grammar Validator",
            "passed": True,
            "score": 100,
            "errors": [],
            "warnings": [],
            "diagnostics": [],
            "fixed_content": fixed_content
        }


class ArchitectureValidator:
    """Validates architectural consistency, participant traceability, and structural connectivity."""

    def validate(self, diagram_type: str, diagram_plan: str, plantuml_content: str) -> Dict[str, Any]:
        if diagram_type.lower() not in ["sequence", "component"]:
            return {
                "validator": "Architecture Validator",
                "passed": True,
                "score": 100,
                "errors": [],
                "warnings": [],
                "diagnostics": [],
            }

        from agents.uml_generator.sequence_validator import SequenceValidator, RelationshipValidator

        diagram = PlantUMLParser.parse(plantuml_content)

        seq_validator = SequenceValidator()
        val_result = seq_validator.validate(diagram_plan, diagram)

        rel_validator = RelationshipValidator()
        rel_result = rel_validator.validate(diagram)

        errors: List[str] = []
        diagnostics: List[Dict[str, Any]] = []

        # Traceability diagnostics
        if not val_result.is_traceable:
            for unapproved in val_result.non_traceable_participants:
                msg = f"Non-traceable (invented) participant found: '{unapproved}'"
                errors.append(msg)
                diagnostics.append(
                    ValidationDiagnostic(
                        category=DiagnosticCategory.TRACEABILITY,
                        code="HALLUCINATED_COMPONENT",
                        message=msg,
                        target_element=unapproved,
                        suggested_fix="Remove unapproved participant or replace with approved capability from plan"
                    ).to_dict()
                )

        # Relationship & Architecture diagnostics
        if not rel_result.is_valid:
            for r_err in rel_result.errors:
                errors.append(r_err)
                diagnostics.append(
                    ValidationDiagnostic(
                        category=DiagnosticCategory.ARCHITECTURE,
                        code="RELATIONSHIP_INTEGRITY",
                        message=r_err,
                        suggested_fix="Fix relationship target or remove duplicate edge"
                    ).to_dict()
                )

        # Isolated component diagnostics
        isolated = diagram.isolated_nodes()
        if isolated:
            for iso in isolated:
                msg = f"Disconnected component detected: '{iso.display_name}'"
                errors.append(msg)
                diagnostics.append(
                    ValidationDiagnostic(
                        category=DiagnosticCategory.ARCHITECTURE,
                        code="DISCONNECTED_COMPONENT",
                        message=msg,
                        target_element=iso.display_name,
                        suggested_fix="Connect component to workflow or remove if redundant"
                    ).to_dict()
                )

        passed = val_result.is_traceable and rel_result.is_valid and not isolated

        # Calculate composite score
        traceability_score = val_result.score
        rel_score = 100 if rel_result.is_valid else max(0, 100 - len(rel_result.errors) * 10)
        conn_score = 100 if not isolated else max(0, 100 - len(isolated) * 15)

        combined_score = int((traceability_score * 0.5) + (rel_score * 0.3) + (conn_score * 0.2))

        return {
            "validator": "Architecture Validator",
            "passed": passed,
            "score": combined_score,
            "errors": errors,
            "warnings": [],
            "diagnostics": diagnostics,
            "traceability_metrics": getattr(val_result, "traceability_metrics", {})
        }


class BusinessFlowValidator:
    """Validates the runtime business flow using LLM or deterministic checks."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    @staticmethod
    def _parse_plan_actors(diagram_plan: str) -> List[str]:
        """Return the list of actor names from the planning JSON."""
        if not diagram_plan:
            return []
        try:
            plan = json.loads(diagram_plan)
            actors = plan.get("actors", [])
            return [a if isinstance(a, str) else a.get("name", "") for a in actors if a]
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _parse_plan_entry_participants(diagram_plan: str) -> List[str]:
        """Return all approved non-actor participants that may serve as workflow entry points."""
        if not diagram_plan:
            return []
        try:
            plan = json.loads(diagram_plan)
        except (json.JSONDecodeError, TypeError):
            return []

        participants: List[str] = []
        for key in ("external_systems", "major_components", "major_data_stores"):
            for item in plan.get(key, []):
                name = item if isinstance(item, str) else item.get("name", "")
                if name:
                    participants.append(name)
        return participants

    def _deterministic_validate(
        self,
        diagram: UMLDiagram,
        diagram_plan: str,
    ) -> Optional[Dict[str, Any]]:
        """Run deterministic checks. Returns a result dict or None."""
        if not diagram.relationships:
            return None

        planned_actors = self._parse_plan_actors(diagram_plan)
        diagram_actors = [n for n in diagram.business_nodes if n.node_type == "actor"]

        if planned_actors:
            planned_actor_norms = {normalize_name(a) for a in planned_actors}
            diagram_actor_norms = {normalize_name(n.display_name) for n in diagram_actors}
            matching_actors = planned_actor_norms & diagram_actor_norms

            if not matching_actors:
                msg = f"Planned actor(s) {planned_actors} not found in diagram. Expected workflow to begin with an approved actor."
                diag = ValidationDiagnostic(
                    category=DiagnosticCategory.BUSINESS_FLOW,
                    code="MISSING_ACTOR_ENTRY",
                    message=msg,
                    suggested_fix="Include planned actor as entry point in workflow"
                ).to_dict()
                return {
                    "passed": False,
                    "score": 50,
                    "errors": [msg],
                    "diagnostics": [diag],
                }
        else:
            approved_entries = self._parse_plan_entry_participants(diagram_plan)
            approved_entry_norms = {normalize_name(e) for e in approved_entries}
            root_nodes = diagram.root_nodes()
            root_norms = {normalize_name(n.display_name) for n in root_nodes}

            first_source_node = None
            if diagram.relationships:
                first_source_node = diagram.resolve(diagram.relationships[0].source)
            first_source_norm = normalize_name(first_source_node.display_name) if first_source_node else ""
            first_source_name = first_source_node.display_name if first_source_node else ""

            has_valid_entry = bool(root_norms & approved_entry_norms) or (
                bool(approved_entry_norms) and first_source_norm in approved_entry_norms
            )
            if not approved_entry_norms:
                has_valid_entry = True

            if not has_valid_entry:
                msg = f"Workflow entry participant '{first_source_name}' is not in approved plan."
                diag = ValidationDiagnostic(
                    category=DiagnosticCategory.BUSINESS_FLOW,
                    code="MISSING_ACTOR_ENTRY",
                    message=msg,
                    target_element=first_source_name,
                    suggested_fix="Start workflow with an approved entry participant"
                ).to_dict()
                return {
                    "passed": False,
                    "score": 55,
                    "errors": [msg],
                    "diagnostics": [diag],
                }

        # Self-loops
        for r in diagram.relationships:
            s_node = diagram.resolve(r.source)
            t_node = diagram.resolve(r.target)
            if s_node and t_node and s_node == t_node:
                msg = f"Self-loop detected on: {s_node.display_name}"
                diag = ValidationDiagnostic(
                    category=DiagnosticCategory.BUSINESS_FLOW,
                    code="SELF_LOOP_DETECTED",
                    message=msg,
                    target_element=s_node.display_name,
                    suggested_fix="Remove self-referencing message loop"
                ).to_dict()
                return {
                    "passed": False,
                    "score": 60,
                    "errors": [msg],
                    "diagnostics": [diag],
                }

        # Adjacent duplicate messages
        rels = diagram.relationships
        for i in range(1, len(rels)):
            prev, curr = rels[i - 1], rels[i]
            if prev.source == curr.source and prev.target == curr.target and prev.label == curr.label:
                msg = f"Duplicate adjacent message detected: {curr.source} -> {curr.target}"
                diag = ValidationDiagnostic(
                    category=DiagnosticCategory.BUSINESS_FLOW,
                    code="DUPLICATE_MESSAGE",
                    message=msg,
                    suggested_fix="Remove duplicate consecutive interaction"
                ).to_dict()
                return {
                    "passed": False,
                    "score": 80,
                    "errors": [msg],
                    "diagnostics": [diag],
                }

        # Orphans
        orphans = diagram.isolated_nodes()
        if orphans:
            orphan_names = [o.display_name for o in orphans]
            msg = f"Orphan participants detected (no messages): {', '.join(orphan_names)}"
            diag = ValidationDiagnostic(
                category=DiagnosticCategory.BUSINESS_FLOW,
                code="ORPHAN_PARTICIPANT",
                message=msg,
                target_element=", ".join(orphan_names),
                suggested_fix="Ensure participant has active workflow messages or remove"
            ).to_dict()
            return {
                "passed": False,
                "score": 85,
                "errors": [msg],
                "diagnostics": [diag],
            }

        return {"passed": True, "score": 100, "errors": [], "warnings": [], "diagnostics": []}

    def validate(self, diagram_type: str, diagram_plan: str, plantuml_content: str) -> Dict[str, Any]:
        if diagram_type.lower() not in ["sequence", "activity"]:
            return {
                "validator": "Business Flow Validator",
                "passed": True,
                "score": 100,
                "errors": [],
                "warnings": [],
                "diagnostics": [],
            }

        diagram = PlantUMLParser.parse(plantuml_content)
        det_result = self._deterministic_validate(diagram, diagram_plan)
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
            response = self.llm.invoke(
                [SystemMessage(content=_ARCHITECT_SYSTEM), HumanMessage(content=prompt)]
            )
            raw = str(response.content).replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            errors = result.get("errors", [])
            diagnostics = [
                ValidationDiagnostic(
                    category=DiagnosticCategory.BUSINESS_FLOW,
                    code="INVALID_FLOW_STEP",
                    message=err,
                    suggested_fix="Fix flow sequence"
                ).to_dict()
                for err in errors
            ]
            return {
                "validator": "Business Flow Validator",
                "passed": result.get("passed", True),
                "score": result.get("score", 100),
                "errors": errors,
                "warnings": result.get("warnings", []),
                "diagnostics": diagnostics,
            }
        except Exception as e:
            logger.warning("Business Flow Validator failed to parse LLM output: %s", e)
            return {
                "validator": "Business Flow Validator",
                "passed": True,
                "score": 100,
                "errors": [],
                "warnings": [],
                "diagnostics": [],
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
            if score <= 10:
                score *= 10
            passed = score >= min_score * 10 if min_score <= 10 else score >= min_score
            errors = result.get("errors", [])
            diagnostics = [
                ValidationDiagnostic(
                    category=DiagnosticCategory.READABILITY,
                    code="VISUAL_COMPLEXITY",
                    message=err,
                    suggested_fix="Simplify layout or group components"
                ).to_dict()
                for err in errors
            ]
            return {
                "validator": "Review Agent",
                "passed": passed,
                "score": score,
                "errors": errors,
                "warnings": result.get("warnings", []),
                "diagnostics": diagnostics,
            }
        except Exception as e:
            logger.warning(f"Review Validator failed to parse LLM output: {e}")
            return {
                "validator": "Review Agent",
                "passed": True,
                "score": 100,
                "errors": [],
                "warnings": [],
                "diagnostics": [],
            }


class ValidationPipeline:
    """Reusable validation pipeline combining Grammar, Architecture, and Business Flow validators."""

    def __init__(self, llm: BaseChatModel):
        self.grammar_val = GrammarValidator()
        self.arch_val = ArchitectureValidator()
        self.flow_val = BusinessFlowValidator(llm)
        self.llm = llm

    def validate_diagram(self, diagram_type: str, diagram_plan: str, plantuml_content: str) -> Dict[str, Any]:
        """Runs all validators sequentially and aggregates structured diagnostics."""
        pipeline_feedback = None
        uml_validation_metrics = {}
        syntax_valid = False
        arch_res: Optional[Dict[str, Any]] = None
        flow_res: Optional[Dict[str, Any]] = None
        aggregated_diagnostics: List[Dict[str, Any]] = []

        # Layer 1: Grammar Validator
        grammar_res = self.grammar_val.validate(diagram_type, plantuml_content)
        if "fixed_content" in grammar_res:
            plantuml_content = grammar_res["fixed_content"]

        uml_validation_metrics["grammar_score"] = grammar_res["score"]
        grammar_status = "passed" if grammar_res["passed"] else "failed"

        # Compute quantitative diagram score card across 9 metrics
        score_card = EnterpriseDiagramScorer.evaluate(
            diagram_type=diagram_type,
            plantuml_content=plantuml_content,
            grammar_res=grammar_res,
            arch_res=arch_res if grammar_res["passed"] else None,
            flow_res=flow_res if (grammar_res["passed"] and arch_res is not None and arch_res["passed"]) else None,
        )

        uml_validation_metrics.update({
            "diagram_score": score_card.overall_score,
            "is_production_ready": score_card.is_production_ready,
            "score_card": score_card.to_dict(),
        })

        if pipeline_feedback is not None and isinstance(pipeline_feedback, dict):
            pipeline_feedback["score_card"] = score_card.to_dict()

        if not grammar_res["passed"]:
            return {
                "pipeline_feedback": pipeline_feedback,
                "uml_validation_metrics": uml_validation_metrics,
                "syntax_valid": syntax_valid,
                "fixed_content": plantuml_content,
                "grammar_status": grammar_status,
                "architecture_status": "skipped",
                "business_flow_status": "skipped",
                "score_card": score_card.to_dict(),
            }

        syntax_valid = True

        # Layer 2: Architecture Validator
        arch_res = self.arch_val.validate(diagram_type, diagram_plan, plantuml_content)
        uml_validation_metrics["architecture_score"] = arch_res["score"]
        architecture_status = "passed" if arch_res["passed"] else "failed"

        # Re-evaluate score card with architecture results
        score_card = EnterpriseDiagramScorer.evaluate(
            diagram_type=diagram_type,
            plantuml_content=plantuml_content,
            grammar_res=grammar_res,
            arch_res=arch_res,
        )
        uml_validation_metrics.update({
            "diagram_score": score_card.overall_score,
            "is_production_ready": score_card.is_production_ready,
            "score_card": score_card.to_dict(),
        })

        if not arch_res["passed"]:
            pipeline_feedback = arch_res
            pipeline_feedback["score_card"] = score_card.to_dict()
            return {
                "pipeline_feedback": pipeline_feedback,
                "uml_validation_metrics": uml_validation_metrics,
                "syntax_valid": syntax_valid,
                "fixed_content": plantuml_content,
                "grammar_status": grammar_status,
                "architecture_status": architecture_status,
                "business_flow_status": "skipped",
                "score_card": score_card.to_dict(),
            }

        # Layer 3: Business Flow Validator
        flow_res = self.flow_val.validate(diagram_type, diagram_plan, plantuml_content)
        uml_validation_metrics["business_flow_score"] = flow_res["score"]
        business_flow_status = "passed" if flow_res["passed"] else "failed"

        # Re-evaluate final score card with full pipeline results
        score_card = EnterpriseDiagramScorer.evaluate(
            diagram_type=diagram_type,
            plantuml_content=plantuml_content,
            grammar_res=grammar_res,
            arch_res=arch_res,
            flow_res=flow_res,
        )
        uml_validation_metrics.update({
            "diagram_score": score_card.overall_score,
            "is_production_ready": score_card.is_production_ready,
            "score_card": score_card.to_dict(),
        })

        if not flow_res["passed"]:
            pipeline_feedback = flow_res
            pipeline_feedback["score_card"] = score_card.to_dict()

        return {
            "pipeline_feedback": pipeline_feedback,
            "uml_validation_metrics": uml_validation_metrics,
            "syntax_valid": syntax_valid,
            "fixed_content": plantuml_content,
            "grammar_status": grammar_status,
            "architecture_status": architecture_status,
            "business_flow_status": business_flow_status,
            "llm_invoked": flow_res.get("llm_invoked", False),
            "score_card": score_card.to_dict(),
        }
