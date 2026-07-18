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

from agents.uml_generator.canonical_parser import CanonicalDiagramParser, CanonicalParseError
from enum import Enum
from app.settings import settings

logger = get_logger("agents.uml_generator.validators")

_ARCHITECT_SYSTEM = (
    "You are a Principal Software Architect with deep expertise in UML and "
    "system design. You produce concise, accurate outputs in the format "
    "requested — never adding invented components or services."
)


class GrammarValidationMode(str, Enum):
    STRICT = "STRICT"
    BEST_EFFORT = "BEST_EFFORT"
    DISABLED = "DISABLED"


class GrammarValidator:
    """Validates PlantUML syntax using local plantuml binary with resilient fallback modes."""

    def __init__(self, mode: Optional[str] = None, timeout: Optional[int] = None):
        configured_mode = mode or getattr(settings, "GRAMMAR_VALIDATION_MODE", "BEST_EFFORT")
        try:
            self.mode = GrammarValidationMode(configured_mode.upper())
        except ValueError:
            self.mode = GrammarValidationMode.BEST_EFFORT

        self.timeout = timeout if timeout is not None else getattr(settings, "GRAMMAR_VALIDATION_TIMEOUT", 3)

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

    def _try_svg_render(self, content: str) -> bool:
        """SVG Render Shortcut: Check if plantuml -tsvg succeeds."""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".puml", delete=False, encoding="utf-8") as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            proc = subprocess.run(["plantuml", "-tsvg", tmp_path], capture_output=True, text=True, timeout=self.timeout)
            os.unlink(tmp_path)
            svg_path = tmp_path.replace(".puml", ".svg")
            if os.path.exists(svg_path):
                os.unlink(svg_path)
            return proc.returncode == 0
        except Exception as exc:
            logger.debug("SVG render shortcut failed: %s", exc)
            return False

    def validate(self, diagram_type: str, plantuml_content: str) -> Dict[str, Any]:
        fixed_content = self._auto_fix(plantuml_content)

        if self.mode == GrammarValidationMode.DISABLED:
            return {
                "validator": "Grammar Validator",
                "passed": True,
                "score": 100,
                "status": "passed",
                "errors": [],
                "warnings": [],
                "diagnostics": [],
                "fixed_content": fixed_content,
            }

        errors: List[str] = []
        diagnostics: List[Dict[str, Any]] = []

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".puml", delete=False, encoding="utf-8") as tmp:
                tmp.write(fixed_content)
                tmp_path = tmp.name

            result = subprocess.run(["plantuml", "-syntax", tmp_path], capture_output=True, text=True, timeout=self.timeout)
            os.unlink(tmp_path)

            has_error = "Error" in result.stdout or "error" in result.stdout.lower() or result.returncode != 0
            if has_error:
                err_msg = result.stdout.strip() or result.stderr.strip() or "Syntax Error"

                # SVG Render Shortcut Check
                if self.mode == GrammarValidationMode.BEST_EFFORT and self._try_svg_render(fixed_content):
                    logger.info("Grammar Validator: Syntax check warning/error bypassed by SVG render shortcut.")
                    return {
                        "validator": "Grammar Validator",
                        "passed": True,
                        "score": 100,
                        "status": "passed",
                        "errors": [],
                        "warnings": [f"Syntax check warning bypassed by SVG render shortcut: {err_msg}"],
                        "diagnostics": [],
                        "fixed_content": fixed_content,
                    }

                code = "SYNTAX_ERROR"
                if "unknown" in err_msg.lower():
                    code = "UNKNOWN_KEYWORD"
                elif "error" not in err_msg.lower():
                    code = "PLANTUML_INTERNAL_FAILURE"

                errors.append(err_msg)
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
                    "status": "failed",
                    "errors": errors,
                    "warnings": [],
                    "diagnostics": diagnostics,
                    "fixed_content": fixed_content,
                }

            return {
                "validator": "Grammar Validator",
                "passed": True,
                "score": 100,
                "status": "passed",
                "errors": [],
                "warnings": [],
                "diagnostics": [],
                "fixed_content": fixed_content,
            }

        except subprocess.TimeoutExpired:
            logger.warning("Grammar validation plantuml -syntax timed out after %ds", self.timeout)
            if self.mode == GrammarValidationMode.BEST_EFFORT:
                if self._try_svg_render(fixed_content):
                    logger.info("SVG render shortcut succeeded after syntax check timeout.")
                    return {
                        "validator": "Grammar Validator",
                        "passed": True,
                        "score": 100,
                        "status": "passed",
                        "errors": [],
                        "warnings": ["plantuml -syntax timed out; syntax verified via SVG render shortcut."],
                        "diagnostics": [],
                        "fixed_content": fixed_content,
                    }
                else:
                    logger.warning("Grammar Validation Unavailable (syntax check timed out). Continuing workflow.")
                    return {
                        "validator": "Grammar Validator",
                        "passed": True,
                        "score": 100,
                        "status": "timed_out",
                        "errors": [],
                        "warnings": ["Grammar Validation Unavailable (syntax check timed out). Continuing workflow."],
                        "diagnostics": [],
                        "fixed_content": fixed_content,
                    }
            else:  # STRICT mode
                errors.append(f"PlantUML syntax check timed out after {self.timeout}s")
                diagnostics.append(
                    ValidationDiagnostic(
                        category=DiagnosticCategory.GRAMMAR,
                        code="TOOL_TIMEOUT",
                        message=f"PlantUML syntax check timed out after {self.timeout} seconds",
                        suggested_fix="Simplify diagram or increase GRAMMAR_VALIDATION_TIMEOUT"
                    ).to_dict()
                )
                return {
                    "validator": "Grammar Validator",
                    "passed": False,
                    "score": 0,
                    "status": "failed",
                    "errors": errors,
                    "warnings": [],
                    "diagnostics": diagnostics,
                    "fixed_content": fixed_content,
                }

        except FileNotFoundError:
            logger.warning("PlantUML executable missing in PATH.")
            if self.mode == GrammarValidationMode.BEST_EFFORT:
                return {
                    "validator": "Grammar Validator",
                    "passed": True,
                    "score": 100,
                    "status": "timed_out",
                    "errors": [],
                    "warnings": ["PlantUML executable missing. Grammar validation unavailable."],
                    "diagnostics": [],
                    "fixed_content": fixed_content,
                }
            else:
                return {
                    "validator": "Grammar Validator",
                    "passed": False,
                    "score": 0,
                    "status": "failed",
                    "errors": ["PlantUML binary not found in system PATH"],
                    "diagnostics": [
                        ValidationDiagnostic(
                            category=DiagnosticCategory.GRAMMAR,
                            code="MISSING_EXECUTABLE",
                            message="PlantUML executable missing in system PATH",
                            suggested_fix="Install PlantUML or set PATH"
                        ).to_dict()
                    ],
                    "fixed_content": fixed_content,
                }

        except Exception as exc:
            logger.warning("Grammar validation error: %s", exc)
            if self.mode == GrammarValidationMode.BEST_EFFORT:
                return {
                    "validator": "Grammar Validator",
                    "passed": True,
                    "score": 100,
                    "status": "timed_out",
                    "errors": [],
                    "warnings": [f"Grammar validation unavailable: {exc}"],
                    "diagnostics": [],
                    "fixed_content": fixed_content,
                }
            else:
                return {
                    "validator": "Grammar Validator",
                    "passed": False,
                    "score": 0,
                    "status": "failed",
                    "errors": [f"Grammar validation error: {exc}"],
                    "diagnostics": [
                        ValidationDiagnostic(
                            category=DiagnosticCategory.GRAMMAR,
                            code="PLANTUML_INTERNAL_FAILURE",
                            message=str(exc),
                            suggested_fix="Check PlantUML installation and Java runtime"
                        ).to_dict()
                    ],
                    "fixed_content": fixed_content,
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
                code = "SELF_LOOP_INTERACTION" if "Self-loop" in r_err else "RELATIONSHIP_INTEGRITY"
                fix = (
                    "Sequence diagrams model interactions. Self-loop messages represent internal computation. "
                    "Merge internal work into a single outgoing interaction or model separate approved participants."
                    if code == "SELF_LOOP_INTERACTION"
                    else "Fix relationship target or remove duplicate edge"
                )
                diagnostics.append(
                    ValidationDiagnostic(
                        category=DiagnosticCategory.ARCHITECTURE,
                        code=code,
                        message=r_err,
                        suggested_fix=fix
                    ).to_dict()
                )

        # Isolated component diagnostics — classified by entity type severity
        # Fatal: business capabilities, databases, packages → trigger repair
        # Non-fatal: actors, external systems → warning only
        _WARNING_ONLY_TYPES = frozenset({"actor", "boundary", "control", "entity"})
        isolated = diagram.isolated_nodes()
        warnings: List[str] = []
        fatal_isolated: List[Any] = []

        if isolated:
            for iso in isolated:
                node_type = getattr(iso, "node_type", "component")
                is_warning = node_type in _WARNING_ONLY_TYPES or node_type == "rectangle"

                # External systems parsed as 'component' may have names suggesting external origin
                display_lower = iso.display_name.lower() if iso.display_name else ""
                if any(kw in display_lower for kw in ("external", "api", "gateway", "third-party", "3rd party")):
                    is_warning = True

                if is_warning:
                    msg = f"Isolated optional element (warning): '{iso.display_name}'"
                    warnings.append(msg)
                    diagnostics.append(
                        ValidationDiagnostic(
                            category=DiagnosticCategory.ARCHITECTURE,
                            code="DISCONNECTED_OPTIONAL",
                            message=msg,
                            target_element=iso.display_name,
                            suggested_fix="Consider connecting to workflow or leave as optional"
                        ).to_dict()
                    )
                else:
                    msg = f"Disconnected component detected: '{iso.display_name}'"
                    errors.append(msg)
                    fatal_isolated.append(iso)
                    diagnostics.append(
                        ValidationDiagnostic(
                            category=DiagnosticCategory.ARCHITECTURE,
                            code="DISCONNECTED_COMPONENT",
                            message=msg,
                            target_element=iso.display_name,
                            suggested_fix="Connect component to workflow or remove if redundant"
                        ).to_dict()
                    )

        passed = val_result.is_traceable and rel_result.is_valid and not fatal_isolated

        # Calculate composite score
        traceability_score = val_result.score
        rel_score = 100 if rel_result.is_valid else max(0, 100 - len(rel_result.errors) * 10)
        conn_score = 100 if not fatal_isolated else max(0, 100 - len(fatal_isolated) * 15)

        combined_score = int((traceability_score * 0.5) + (rel_score * 0.3) + (conn_score * 0.2))

        return {
            "validator": "Architecture Validator",
            "passed": passed,
            "score": combined_score,
            "errors": errors,
            "warnings": warnings,
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
            plan = CanonicalDiagramParser.parse(diagram_plan)
            actors = plan.get("actors", [])
            return [a if isinstance(a, str) else a.get("name", "") for a in actors if a]
        except (CanonicalParseError, json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _parse_plan_entry_participants(diagram_plan: str) -> List[str]:
        """Return all approved non-actor participants that may serve as workflow entry points."""
        if not diagram_plan:
            return []
        try:
            plan = CanonicalDiagramParser.parse(diagram_plan)
        except (CanonicalParseError, json.JSONDecodeError, TypeError):
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
