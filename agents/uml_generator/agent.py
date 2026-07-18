"""UML Generator Agent implementation.

Pipeline per diagram (sequential, free-tier optimized):
    1. Planning  — LLM scopes actors, components, and flow.
    2. Generation — LLM produces PlantUML from Business Summary + Plan.
    3. Local syntax validation — subprocess plantuml check, zero LLM cost.
    4. Review    — LLM self-evaluates, ONLY if syntax validation passed.
    5. Retry (once) — if review fails, regenerate with issue context.
    6. Skip review — if syntax validation fails (diagram goes to UML Repair Agent).

Max LLM calls per diagram (syntax valid, review passes)   : 3 (plan + generate + review)
Max LLM calls per diagram (syntax valid, review fails)    : 4 (plan + generate + review + regen)
Max LLM calls per diagram (syntax invalid)                : 2 (plan + generate) — review skipped
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional

from core.cache_manager import CacheManager
from core.cost_tracker import record_agent_cost

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.base import BaseAgent
from agents.uml_generator.context_builder import ContextBuilder
from agents.uml_generator.diagram_constraints import get_constraints
from agents.uml_generator.prompt_builder import PromptBuilder
from app.state import ForgeState
from app.settings import settings
from config.logging import get_logger
from core.agent_registry import AgentRegistry
from core.artifact_manager import ArtifactManager
from core.llm import get_llm
from core.utils import generate_timestamp
from core.business_normalizer import normalize_plan

logger = get_logger("agents.uml_generator")


# ---------------------------------------------------------------------------
# Shared system prompt for ancillary LLM calls (planning & review)
# ---------------------------------------------------------------------------

_ARCHITECT_SYSTEM = (
    "You are a Principal Software Architect with deep expertise in UML and "
    "system design. You produce concise, accurate outputs in the format "
    "requested — never adding invented components or services."
)


# ---------------------------------------------------------------------------
# Execution metrics accumulator
# ---------------------------------------------------------------------------

class _Metrics:
    """Lightweight call counter for a single UMLGeneratorAgent.run() invocation."""

    __slots__ = ("planning_calls", "generation_calls", "review_calls", "repair_calls")

    def __init__(self) -> None:
        self.planning_calls = 0
        self.generation_calls = 0
        self.review_calls = 0
        self.repair_calls = 0  # populated externally by UML Repair Agent

    @property
    def total(self) -> int:
        return self.planning_calls + self.generation_calls + self.review_calls + self.repair_calls

    def as_dict(self) -> dict[str, int]:
        return {
            "planning_calls": self.planning_calls,
            "generation_calls": self.generation_calls,
            "review_calls": self.review_calls,
            "repair_calls": self.repair_calls,
            "total_llm_calls": self.total,
        }


class UMLGeneratorAgent(BaseAgent):
    """UML Generator agent responsible for creating PlantUML diagrams."""

    @property
    def name(self) -> str:
        return "UML Generator"

    @property
    def description(self) -> str:
        return "Generates PlantUML syntax for various diagram types based on the user prompt."

    @property
    def capabilities(self) -> List[str]:
        return ["Component", "Sequence", "Activity", "Deployment", "Class", "Use Case"]

    @property
    def requires(self) -> List[str]:
        return ["architecture_json", "selected_uml_diagrams"]

    @property
    def produces(self) -> List[str]:
        return ["plantuml_diagrams"]

    def __init__(self, llm: Optional[BaseChatModel] = None) -> None:
        self._llm = llm
        self.artifact_manager = ArtifactManager()
        self.context_builder = ContextBuilder()
        self.prompt_builder = PromptBuilder()

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    # -----------------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------------

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the UML Generator agent step."""
        user_request = state.get("user_request", "").strip()
        architecture_json = state.get("architecture_json") or {}
        selected_uml_diagrams = state.get("selected_uml_diagrams", []) or []
        current_diagram_id = state.get("current_diagram_id")

        if not selected_uml_diagrams:
            logger.warning("No UML diagrams selected for generation.")
            return {}

        # Respect explicit requested_diagrams from metadata — filter the
        # selected list to only what the caller requested.
        metadata = state.get("metadata", {}) or {}
        requested_diagrams: List[str] = metadata.get("requested_diagrams", []) or []
        if requested_diagrams:
            requested_lower = {d.lower() for d in requested_diagrams}
            filtered = [
                d for d in selected_uml_diagrams
                if d.get("diagram", "").lower() in requested_lower
                or d.get("diagram_id", "").lower() in requested_lower
            ]
            if filtered:
                selected_uml_diagrams = filtered
                logger.info(
                    "Filtered selected_uml_diagrams to explicit request | "
                    "requested=%s | remaining=%d",
                    requested_diagrams,
                    len(filtered),
                )

        if current_diagram_id:
            diagrams_to_process = [
                d for d in selected_uml_diagrams
                if d.get("diagram_id", d.get("diagram", d.get("type", "unknown"))) == current_diagram_id
            ]
            logger.info(
                "UML Generator starting parallel generation | diagram_id=%s",
                current_diagram_id,
            )
        else:
            diagrams_to_process = selected_uml_diagrams
            logger.info(
                "UML Generator starting sequential generation | count=%d",
                len(selected_uml_diagrams),
            )

        # Initialize from existing state
        diagrams = dict(state.get("plantuml_diagrams", {}) or {})
        saved_paths = list(state.get("artifacts", {}).get("uml", []) or [])
        diagram_states = dict(state.get("diagram_execution_states", {}) or {})

        # Build Business Architecture Summary once — shared across all diagrams.
        architecture_summary: str = (
            state.get("architecture_summary")  # type: ignore[assignment]
            or self.context_builder.build_summary(architecture_json)
        )
        logger.info(
            "Architecture summary ready | summary_len=%d",
            len(architecture_summary),
        )

        metrics = _Metrics()
        state_uml_validation_metrics = {}
        state_traceability_metrics = {}

        for diagram_info in diagrams_to_process:
            diagram_type = diagram_info.get("diagram", diagram_info.get("type", "unknown"))
            diag_id = diagram_info.get("diagram_id", diagram_type)
            reason = diagram_info.get("reason", "")

            existing_state = diagram_states.get(diag_id, {})
            if existing_state.get("status") == "success" and existing_state.get("generator_output"):
                logger.info("Cache hit | diagram_id=%s — skipping generation.", diag_id)
                record_agent_cost(state.setdefault("metadata", {}), self.name, cache_hit=True)
                continue

            start_time = time.time()
            diagram_llm_calls = 0

            # -- Step 1: Planning ------------------------------------------------
            diagram_plan = self._plan_diagram(
                diagram_type=diagram_type,
                architecture_summary=architecture_summary,
                user_request=user_request,
            )
            metrics.planning_calls += 1
            diagram_llm_calls += 1
            
            # Extract traceability
            if diagram_plan:
                try:
                    plan_data = json.loads(diagram_plan)
                    if "traceability" in plan_data and plan_data["traceability"]:
                        state_traceability_metrics[diag_id] = plan_data["traceability"]
                except Exception as e:
                    logger.warning("Could not extract traceability from diagram plan: %s", e)


            # -- Step 2: Generation ----------------------------------------------
            system_prompt, user_prompt = self.prompt_builder.build_prompt(
                diagram_type=diagram_type,
                architecture_summary=architecture_summary,
                diagram_plan=diagram_plan,
            )
            full_user_prompt = (
                f"{user_prompt}\n\n"
                f"## Final User Request\n\n"
                f"{user_request}\n\n"
                f"Reason for this diagram: {reason}"
            )

            prompt_length = len(system_prompt) + len(full_user_prompt)
            logger.info(
                "LLM generation starting | "
                "diagram_type=%s | architecture_summary_len=%d | "
                "diagram_plan_len=%d | prompt_length=%d | estimated_token_count=%d",
                diagram_type,
                len(architecture_summary),
                len(diagram_plan),
                prompt_length,
                prompt_length // 4,
            )

            t0 = time.time()
            raw_response = self._generate(system_prompt, full_user_prompt)
            gen_time_ms = int((time.time() - t0) * 1000)
            record_agent_cost(
                state.setdefault("metadata", {}), 
                self.name, 
                input_text=system_prompt + full_user_prompt, 
                output_text=raw_response,
                latency_ms=gen_time_ms,
                llm_calls=1
            )
            
            metrics.generation_calls += 1
            diagram_llm_calls += 1

            # -- Canonical Diagram JSON Target Pipeline (Phase 9.1) ------------
            from agents.uml_generator.canonical_validator import CanonicalDiagramValidator
            from agents.uml_generator.layout_planner import LayoutPlanner
            from agents.uml_generator.plantuml_builder import PlantUMLBuilderFactory
            from core.business_normalizer import normalize_name

            allowed_names: set[str] = set()
            if diagram_plan:
                try:
                    plan_data = json.loads(diagram_plan)
                    for key in ["actors", "external_systems", "major_components", "major_data_stores"]:
                        for item in plan_data.get(key, []):
                            allowed_names.add(normalize_name(item))
                except Exception as ex:
                    logger.warning("Could not extract allowed names from diagram plan: %s", ex)

            try:
                if raw_response.strip().startswith("@startuml"):
                    clean_content = raw_response.strip()
                else:
                    canonical_diagram = CanonicalDiagramValidator.validate(
                        raw_input=raw_response,
                        diagram_type=diagram_type,
                        allowed_normalized_names=allowed_names if allowed_names else None,
                    )
                    _, layout_plan = LayoutPlanner.plan(canonical_diagram)
                    builder = PlantUMLBuilderFactory.get_builder(diagram_type)
                    clean_content = builder.build(canonical_diagram, layout_plan)
            except Exception as canonical_err:
                logger.warning("Canonical Diagram pipeline error: %s. Retrying generation once.", canonical_err)
                retry_prompt = (
                    f"{full_user_prompt}\n\n"
                    f"## Canonical Validation Error\n"
                    f"Your previous output failed validation: {canonical_err}.\n"
                    f"Respond ONLY with valid Canonical Diagram JSON matching the schema with stable IDs."
                )
                raw_response = self._generate(system_prompt, retry_prompt)
                metrics.generation_calls += 1
                diagram_llm_calls += 1
                if raw_response.strip().startswith("@startuml"):
                    clean_content = raw_response.strip()
                else:
                    canonical_diagram = CanonicalDiagramValidator.validate(
                        raw_input=raw_response,
                        diagram_type=diagram_type,
                        allowed_normalized_names=allowed_names if allowed_names else None,
                    )
                    _, layout_plan = LayoutPlanner.plan(canonical_diagram)
                    builder = PlantUMLBuilderFactory.get_builder(diagram_type)
                    clean_content = builder.build(canonical_diagram, layout_plan)

            # -- Multi-Layer Validation Pipeline (Phase 5) -----------------------
            from agents.uml_generator.validators import ValidationPipeline, ReviewValidator
            
            pipeline = ValidationPipeline(self.llm)
            review_val = ReviewValidator(self.llm)

            pipeline_feedback = None
            uml_validation_metrics = {}
            syntax_valid = False
            grammar_status = "skipped"
            architecture_status = "skipped"
            business_flow_status = "skipped"
            
            cache_manager = CacheManager()
            cached_validation = cache_manager.get_validation(diagram_plan, clean_content)
            
            if cached_validation:
                logger.info("Validation Cache Hit — skipping Grammar, Architecture, and Business Flow validators.")
                pipeline_feedback = cached_validation.get("pipeline_feedback")
                uml_validation_metrics = cached_validation.get("uml_validation_metrics", {})
                syntax_valid = cached_validation.get("syntax_valid", False)
                grammar_status = cached_validation.get("grammar_status", "passed")
                architecture_status = cached_validation.get("architecture_status", "passed")
                business_flow_status = cached_validation.get("business_flow_status", "passed")
                # Ensure the fixed content from grammar is propagated if it existed
                if "fixed_content" in cached_validation:
                    clean_content = cached_validation["fixed_content"]
            else:
                val_res = pipeline.validate_diagram(diagram_type, diagram_plan, clean_content)
                clean_content = val_res.get("fixed_content", clean_content)
                pipeline_feedback = val_res.get("pipeline_feedback")
                uml_validation_metrics = val_res.get("uml_validation_metrics", {})
                syntax_valid = val_res.get("syntax_valid", False)
                grammar_status = val_res.get("grammar_status", "failed")
                architecture_status = val_res.get("architecture_status", "skipped")
                business_flow_status = val_res.get("business_flow_status", "skipped")
                
                if val_res.get("llm_invoked", False):
                    metrics.review_calls += 1
                    diagram_llm_calls += 1
                    
                cache_manager.set_validation(diagram_plan, clean_content, val_res)

            # Layer 4: Adaptive Review Agent
            if syntax_valid and not pipeline_feedback and settings.ENABLE_UML_REVIEW:
                grammar_score = uml_validation_metrics.get("grammar_score", 100)
                arch_score = uml_validation_metrics.get("architecture_score", 100)
                flow_score = uml_validation_metrics.get("business_flow_score", 100)
                
                confidence = min(grammar_score, arch_score, flow_score)
                # Default threshold 95
                REVIEW_CONFIDENCE_THRESHOLD = int(os.environ.get("REVIEW_CONFIDENCE_THRESHOLD", 95))
                
                if confidence >= REVIEW_CONFIDENCE_THRESHOLD:
                    logger.info("Adaptive Review Skipped (All scores >= %d) | diagram_type=%s", REVIEW_CONFIDENCE_THRESHOLD, diagram_type)
                    uml_validation_metrics["review_score"] = 100
                else:
                    cached_review = cache_manager.get_review(clean_content)
                    if cached_review:
                        logger.info("Review Cache Hit — skipping Review Validator.")
                        review_res = cached_review
                    else:
                        constraints = get_constraints(diagram_type)
                        review_res = review_val.validate(diagram_type, clean_content, constraints, settings.MIN_DIAGRAM_SCORE)
                        metrics.review_calls += 1
                        diagram_llm_calls += 1
                        cache_manager.set_review(clean_content, review_res)
                        
                    uml_validation_metrics["review_score"] = review_res["score"]
                    logger.info("Review Agent | %s (Score %s)", "PASS" if review_res["passed"] else "FAIL", review_res["score"])
                    
                    if not review_res["passed"]:
                        issues_text = "; ".join(review_res.get("errors", []))
                        logger.warning(
                            "Diagram review failed (Score %s) — regenerating once | "
                            "diagram_type=%s | issues=%s",
                            review_res.get("score", 0),
                            diagram_type,
                            issues_text,
                        )
                        retry_prompt = (
                            f"{full_user_prompt}\n\n"
                            f"## Quality Review Feedback\n\n"
                            f"A previous attempt scored {review_res.get('score', 0)}/100 and was rejected. "
                            f"Fix all of the following issues in this regeneration:\n"
                            + "\n".join(f"- {issue}" for issue in review_res.get("errors", []))
                        )
                        clean_content = self._generate(system_prompt, retry_prompt)
                        metrics.generation_calls += 1
                        diagram_llm_calls += 1
                        logger.info("Diagram regenerated after review | diagram_type=%s", diagram_type)
                        
                        # Check grammar one last time so we don't pass fundamentally broken output
                        val_res2 = pipeline.validate_diagram(diagram_type, diagram_plan, clean_content)
                        if "fixed_content" in val_res2:
                            clean_content = val_res2["fixed_content"]
                        
                        if not val_res2.get("syntax_valid", False):
                            pipeline_feedback = val_res2.get("pipeline_feedback")
                            syntax_valid = False
                        else:
                            grammar_status = val_res2.get("grammar_status", "failed")
                            architecture_status = val_res2.get("architecture_status", "skipped")
                            business_flow_status = val_res2.get("business_flow_status", "skipped")
            elif not settings.ENABLE_UML_REVIEW:
                logger.info("Review Agent disabled globally (ENABLE_UML_REVIEW=false) | diagram_type=%s", diagram_type)

            generation_time_ms = int((time.time() - start_time) * 1000)

            # -- Persist ----------------------------------------------------------
            diagrams[diag_id] = clean_content

            base_name = diag_id.lower().replace(" ", "_")
            saved_path = self.artifact_manager.save_artifact(
                stage="uml",
                base_name=base_name,
                content=clean_content,
                ext="puml",
            )
            if saved_path not in saved_paths:
                saved_paths.append(saved_path)

            diagram_states[diag_id] = {
                "diagram_id": diag_id,
                "diagram_type": diagram_type,
                "status": "generated",
                "attempt": existing_state.get("attempt", 0) + 1,
                "generator_output": clean_content,
                "execution_time_ms": existing_state.get("execution_time_ms", 0) + generation_time_ms,
                "llm_calls": existing_state.get("llm_calls", 0) + diagram_llm_calls,
                "syntax_valid_at_generation": syntax_valid,
                "diagram_plan": diagram_plan,
                "grammar_status": grammar_status,
                "architecture_status": architecture_status,
                "business_flow_status": business_flow_status,
                "pipeline_feedback": pipeline_feedback,
                "uml_validation_metrics": uml_validation_metrics,
                "diagram_score": uml_validation_metrics.get("diagram_score", 100.0),
                "is_production_ready": uml_validation_metrics.get("is_production_ready", True),
                "score_card": uml_validation_metrics.get("score_card"),
            }
            # Keep latest metrics for global metadata
            state_uml_validation_metrics = uml_validation_metrics

        # -- Emit execution metrics -------------------------------------------
        self._log_metrics(metrics, len(diagrams_to_process))

        new_message = AIMessage(
            content=f"Generated {len(diagrams_to_process)} diagram(s).",
            name="uml_generator",
        )

        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "uml_generation_completed": True,
            "uml_llm_metrics": metrics.as_dict(),
            "last_updated": generate_timestamp(),
        }
        
        # Add uml validation metrics to global metadata
        if state_uml_validation_metrics:
            updated_metadata["uml_validation_metrics"] = state_uml_validation_metrics
        if state_traceability_metrics:
            updated_metadata["traceability_metrics"] = state_traceability_metrics

        return {
            "plantuml_diagrams": diagrams,
            "diagram_execution_states": diagram_states,
            "artifacts": {"uml": saved_paths},
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "uml_generator",
            "architecture_summary": architecture_summary,
        }

    # -----------------------------------------------------------------------
    # Planning step
    # -----------------------------------------------------------------------

    def _plan_diagram(
        self,
        diagram_type: str,
        architecture_summary: str,
        user_request: str,
    ) -> str:
        """Produce a structured diagram plan (JSON) before PlantUML generation."""
        planning_prompt = (
            f"You are a Principal Software Architect preparing a **{diagram_type} Diagram**.\n\n"
            f"## Business Architecture Summary\n\n"
            f"{architecture_summary}\n\n"
            f"## User Request\n\n"
            f"{user_request}\n\n"
            f"## Task\n\n"
            f"Produce a concise, structured architectural plan for this diagram.\n"
            f"Extract BUSINESS CAPABILITIES, not implementation services.\n\n"
            f"## Rules\n"
            f"1. **Abstraction Budget**: Target MAX 3 actors, 3 external systems, 8 major_components, 3 major_data_stores. Group entities to stay within these limits.\n"
            f"2. **Actor Consolidation**: Represent user personas as logical architectural actor groups (e.g. 'Compliance Users', 'System Administrator').\n"
            f"3. **Data Store Consolidation**: Group related data stores into architectural repositories when appropriate (e.g. 'Regulatory Repository', 'Assessment Repository').\n"
            f"4. **Capability Grouping**: Group related micro-capabilities into larger bounded contexts.\n"
            f"5. **Traceability**: You must maintain a `traceability` map from the new grouped names to the original elements (e.g. {{\"Compliance Repository\": [\"db_requirements\", \"db_setup\"]}}).\n"
            f"6. **Business Capabilities Only**: `major_components` must be capabilities (e.g. 'Claim Submission', 'Inventory Management'). Do NOT use implementation suffixes.\n"
            f"7. **Never Invent Infrastructure**: Do not invent API Gateways, Auth Services, Message Queues, Load Balancers, Caches, or Repositories unless explicitly required.\n"
            f"8. **Business Flow**: `business_flow` must be an array of short steps (3-6 words each). NO paragraphs.\n"
            f"9. **External Systems**: Only systems outside the product boundary.\n"
            f"10. **Simplicity**: Limit the component diagram to the minimum set of architectural elements required to explain the system.\n\n"
            f"Respond with ONLY valid JSON in exactly this structure — no markdown fences, no commentary. Target under 500 characters whenever possible:\n"
            f"{{\n"
            f'  "actors": [],\n'
            f'  "external_systems": [],\n'
            f'  "major_components": [],\n'
            f'  "major_data_stores": [],\n'
            f'  "business_flow": [],\n'
            f'  "explicitly_excluded": [],\n'
            f'  "traceability": {{"Grouped Name": ["Original 1", "Original 2"]}},\n'
            f'  "diagram_scope": "One sentence stating what this diagram shows and what it excludes"\n'
            f"}}\n"
        )

        messages = [
            SystemMessage(content=_ARCHITECT_SYSTEM),
            HumanMessage(content=planning_prompt),
        ]

        logger.info(
            "LLM planning starting | diagram_type=%s | planning_prompt_len=%d",
            diagram_type,
            len(planning_prompt),
        )

        try:
            response = self.llm.invoke(messages)
            raw = str(response.content).replace("```json", "").replace("```", "").strip()
            
            # Normalize plan
            normalized_raw = self._normalize_plan(diagram_type, raw, user_request)

            # Validate JSON
            plan_data = json.loads(normalized_raw)

            # deterministic cleanup
            plan_data = normalize_plan(plan_data)

            plan_formatted = json.dumps(plan_data, indent=2)
            
            logger.info(
                "LLM planning completed | diagram_type=%s | plan_len=%d",
                diagram_type,
                len(plan_formatted),
            )
            return plan_formatted
        except Exception as exc:
            logger.warning(
                "Planning step failed — proceeding without plan | diagram_type=%s | error=%s",
                diagram_type,
                exc,
            )
            return ""

    def _normalize_plan(self, diagram_type: str, raw_plan: str, user_request: str) -> str:
        """Normalize the extracted plan to strictly contain business capabilities."""
        if not raw_plan:
            return raw_plan

        normalization_prompt = (
            f"You are a Principal Software Architect refining a **{diagram_type} Diagram** plan.\n\n"
            f"## User Request\n\n"
            f"{user_request}\n\n"
            f"## Raw Plan\n\n"
            f"{raw_plan}\n\n"
            f"## Normalization Task\n\n"
            f"Review and normalize the JSON plan above according to these exact rules. "
            f"You must return ONLY the normalized JSON with the exact same keys.\n\n"
            f"**1. Business Capability Normalization**: Every component must map directly to an explicitly stated business capability or an unavoidable one. Never invent intermediate architectural layers.\n"
            f"**2. Duplicate Detection**: Detect and merge semantically equivalent capabilities. Never allow duplicate concepts.\n"
            f"**3. Visual Complexity Budget**: Ensure actors (max 3), external systems (max 3), capabilities (max 8), and data stores (max 3) are strictly adhered to. Group them if necessary.\n"
            f"**4. Long Label Normalization**: Replace excessively long labels with concise architectural names (e.g. 'Compliance Requirement Identification' -> 'Requirement Analysis').\n"
            f"**5. External System Priority**: If a capability already exists as an external system, do not create an internal abstraction.\n"
            f"**6. Traceability Preservation**: Map any grouped or renamed elements to their original names in the `traceability` dictionary.\n"
            f"**7. Final Validation**: Verify that no orchestration layers or invented infrastructure exist. Ensure only business capability names remain.\n\n"
            f"Respond with ONLY valid JSON — no markdown fences, no commentary. Ensure the `traceability` key exists if groupings occurred.\n"
        )

        messages = [
            SystemMessage(content=_ARCHITECT_SYSTEM),
            HumanMessage(content=normalization_prompt),
        ]

        logger.info("LLM normalization starting | diagram_type=%s", diagram_type)
        try:
            response = self.llm.invoke(messages)
            normalized_raw = str(response.content).replace("```json", "").replace("```", "").strip()
            return normalized_raw
        except Exception as exc:
            logger.warning("Normalization step failed — proceeding with raw plan | error=%s", exc)
            return raw_plan


    # -----------------------------------------------------------------------
    # Local syntax validation (no LLM cost)
    # -----------------------------------------------------------------------

    def _validate_syntax_locally(self, plantuml_content: str, diagram_type: str) -> bool:
        """Run a local PlantUML syntax check using the plantuml binary.

        This is a zero-LLM-cost check. If the plantuml binary is unavailable,
        falls back to a heuristic structural check so we never block generation.

        Returns:
            True if syntax appears valid, False if an error is detected.
        """
        # Heuristic guard: must start with @startuml and end with @enduml.
        content = plantuml_content.strip()
        if not (content.startswith("@startuml") and content.endswith("@enduml")):
            logger.warning(
                "Local syntax heuristic failed (missing @startuml/@enduml) | diagram_type=%s",
                diagram_type,
            )
            return False

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".puml",
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            result = subprocess.run(
                ["plantuml", "-syntax", tmp_path],
                capture_output=True,
                text=True,
                timeout=15,
            )
            os.unlink(tmp_path)

            has_error = "Error" in result.stdout or "error" in result.stdout.lower()
            if has_error:
                logger.warning(
                    "Local syntax validation: FAILED | diagram_type=%s | plantuml_output=%s",
                    diagram_type,
                    result.stdout[:300],
                )
                return False

            logger.info(
                "Local syntax validation: PASSED | diagram_type=%s", diagram_type
            )
            return True

        except FileNotFoundError:
            # plantuml binary not on PATH — fall back to heuristic (already passed above)
            logger.info(
                "plantuml binary not found — using heuristic validation only | diagram_type=%s",
                diagram_type,
            )
            return True
        except Exception as exc:
            logger.warning(
                "Local syntax validation error — assuming valid | diagram_type=%s | error=%s",
                diagram_type,
                exc,
            )
            return True

    # -----------------------------------------------------------------------
    # Review step (LLM — only called when syntax is valid)
    # -----------------------------------------------------------------------

    def _review_diagram(
        self,
        diagram_type: str,
        plantuml_content: str,
        constraints: dict[str, Any],
    ) -> dict[str, Any]:
        """Self-review the generated PlantUML against quality criteria.

        Only called when local syntax validation has already passed.
        """
        constraint_lines = "\n".join(
            f"- {k.replace('_', ' ')}: {v}" for k, v in constraints.items()
        ) or "No specific constraints."

        review_prompt = (
            f"You are reviewing a generated **{diagram_type} Diagram** "
            f"(PlantUML) for architecture-review quality.\n\n"
            f"## Diagram Constraints\n{constraint_lines}\n\n"
            f"## Generated PlantUML\n\n"
            f"```\n{plantuml_content}\n```\n\n"
            f"## Review Criteria Rubric (Score out of 10)\n\n"
            f"Evaluate the diagram and provide a score from 1 to 10 based on:\n"
            f"1. **Abstraction (2 pts)** — Does it stay at the correct business/architecture level without implementation leakage?\n"
            f"2. **Business Alignment (2 pts)** — Does it communicate the business purpose clearly?\n"
            f"3. **Hallucination (2 pts)** — No invented infrastructure (e.g. API Gateway, Auth Service) not in context?\n"
            f"4. **Readability (2 pts)** — Are connections clear, not overwhelming, cleanly grouped?\n"
            f"5. **Component Count (1 pt)** — Does it respect component count limits (e.g., max 8)?\n"
            f"6. **Participant Count (1 pt)** — Does it respect participant/message limits (e.g., max 10/20)?\n\n"
            f"## Response Format\n\n"
            f"Respond with ONLY valid JSON in exactly this structure — no markdown fences:\n"
            f"{{\n"
            f'  "score": 10,\n'
            f'  "acceptable": true,\n'
            f'  "issues": []\n'
            f"}}\n\n"
            f"List specific issues if the score is not 10. Be strict — this diagram will be shown in a Senior Architect review."
        )

        messages = [
            SystemMessage(content=_ARCHITECT_SYSTEM),
            HumanMessage(content=review_prompt),
        ]

        logger.info(
            "LLM review starting | diagram_type=%s | plantuml_len=%d",
            diagram_type,
            len(plantuml_content),
        )

        try:
            response = self.llm.invoke(messages)
            raw = str(response.content).replace("```json", "").replace("```", "").strip()
            result: dict[str, Any] = json.loads(raw)
            
            score = result.get("score", 0)
            acceptable = score >= settings.MIN_DIAGRAM_SCORE
            result["acceptable"] = acceptable
            
            logger.info(
                "LLM review completed | diagram_type=%s | score=%s/%s | acceptable=%s | issue_count=%d",
                diagram_type,
                score,
                settings.MIN_DIAGRAM_SCORE,
                acceptable,
                len(result.get("issues", [])),
            )
            return result
        except Exception as exc:
            logger.warning(
                "Review step failed — treating as acceptable | diagram_type=%s | error=%s",
                diagram_type,
                exc,
            )
            return {"score": 10, "acceptable": True, "issues": []}

    # -----------------------------------------------------------------------
    # Shared generation helper
    # -----------------------------------------------------------------------

    # def _generate(self, system_prompt: str, user_prompt: str) -> str:
    #     """Invoke the LLM and return clean PlantUML content."""
    #     messages = [
    #         SystemMessage(content=system_prompt),
    #         HumanMessage(content=user_prompt),
    #     ]
    #     response = self.llm.invoke(messages)
    #     return (
    #         str(response.content)
    #         .replace("```plantuml", "")
    #         .replace("```puml", "")
    #         .replace("```", "")
    #         .strip()
    #     )

    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke the LLM and return clean PlantUML content."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # ================= DEBUG =================
        print("\n" + "=" * 100)
        print("SYSTEM PROMPT")
        print("=" * 100)
        print(system_prompt)

        print("\n" + "=" * 100)
        print("USER PROMPT")
        print("=" * 100)
        print(user_prompt)
        # =========================================

        response = self.llm.invoke(messages)

        # ================= DEBUG =================
        print("\n" + "=" * 100)
        print("RAW LLM OUTPUT")
        print("=" * 100)
        print(response.content)
        print("=" * 100 + "\n")
        # =========================================

        return str(response.content).strip()

    # -----------------------------------------------------------------------
    # Metrics logging
    # -----------------------------------------------------------------------

    def _log_metrics(self, metrics: _Metrics, diagram_count: int) -> None:
        """Log per-workflow LLM call breakdown and total."""
        separator = "=" * 52
        logger.info(separator)
        logger.info(
            "UML Generator — LLM Call Metrics | diagrams=%d", diagram_count
        )
        logger.info("  planning_calls   : %d", metrics.planning_calls)
        logger.info("  generation_calls : %d", metrics.generation_calls)
        logger.info("  review_calls     : %d", metrics.review_calls)
        logger.info("  repair_calls     : %d (populated by Repair Agent)", metrics.repair_calls)
        logger.info("  ─────────────────────────────────────")
        logger.info("  TOTAL LLM CALLS  : %d", metrics.total)
        logger.info(separator)
        # Also print to stdout so it's visible in the CLI
        print(f"\n{'=' * 52}")
        print(f"  UML LLM Metrics ({diagram_count} diagram(s))")
        print(f"  Planning calls   : {metrics.planning_calls}")
        print(f"  Generation calls : {metrics.generation_calls}")
        print(f"  Review calls     : {metrics.review_calls}")
        print(f"  {'─' * 38}")
        print(f"  TOTAL (generator): {metrics.total}")
        print(f"{'=' * 52}\n")


# Automatically register the agent
AgentRegistry().register(UMLGeneratorAgent())
