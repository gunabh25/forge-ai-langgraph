"""Phase 7.2 Regression Tests — UML Repair Agent Traceability Synchronization.

Task 9 — Regression Tests verifying:
  1. Generator output → Repair → No new participants introduced
  2. Repair output containing "Scheduler" → rejected before ValidationPipeline
  3. Repair output with "Compliance Reporting Service" → auto-normalized to "Compliance Reporting"
  4. Repair output with "Workflow Engine" → rejected immediately
"""

import json
import unittest
from typing import cast
from unittest.mock import MagicMock, patch

from app.state import ForgeState

from agents.uml_repair.agent import (
    _extract_allowed_participants,
    _check_traceability,
    _apply_lexical_fix,
    _build_structured_feedback,
    _format_allowed_participants_block,
    UMLRepairAgent,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEBI_PLAN_JSON = json.dumps({
    "actors": ["Compliance Officer"],
    "external_systems": ["SEBI Portal"],
    "major_components": [
        "Circular Ingestion",
        "Circular Parsing",
        "Requirements Extraction",
        "Gap Analysis",
        "Impact Assessment",
        "Compliance Reporting",
    ],
    "major_data_stores": ["Compliance Data Store"],
    "business_flow": [
        "Ingest Circular",
        "Parse Circular",
        "Extract Requirements",
        "Analyse Gaps",
        "Assess Impact",
        "Generate Report",
    ],
    "diagram_scope": "SEBI compliance monitoring end-to-end flow.",
})

VALID_SEBI_PUML = """@startuml
actor "Compliance Officer" as CO
participant "Circular Ingestion" as CI
participant "Circular Parsing" as CP
participant "Requirements Extraction" as RE
participant "Gap Analysis" as GA
participant "Impact Assessment" as IA
participant "Compliance Reporting" as CR
database "Compliance Data Store" as CDS
participant "SEBI Portal" as SP

CO -> CI : Upload Circular
CI -> CP : Parse Content
CP -> RE : Extract Requirements
RE -> GA : Identify Gaps
GA -> IA : Assess Impact
IA -> CR : Generate Report
CR -> CDS : Store Report
CR -> CO : Deliver Report
@enduml"""

SCHEDULER_PUML = """@startuml
actor "Compliance Officer" as CO
participant "Circular Ingestion" as CI
participant "Scheduler" as SCH
participant "Gap Analysis" as GA
participant "Compliance Reporting" as CR

CO -> SCH : Trigger
SCH -> CI : Schedule Ingestion
CI -> GA : Analyse Gaps
GA -> CR : Report
@enduml"""

COMPLIANCE_REPORTING_SERVICE_PUML = """@startuml
actor "Compliance Officer" as CO
participant "Circular Ingestion" as CI
participant "Compliance Reporting Service" as CRS

CO -> CI : Upload
CI -> CRS : Generate Report
CRS -> CO : Deliver
@enduml"""

WORKFLOW_ENGINE_PUML = """@startuml
actor "Compliance Officer" as CO
participant "Workflow Engine" as WE
participant "Gap Analysis" as GA
participant "Compliance Reporting" as CR

CO -> WE : Start
WE -> GA : Run Analysis
GA -> CR : Report
@enduml"""


# ---------------------------------------------------------------------------
# Unit Tests — pure helper functions (no LLM)
# ---------------------------------------------------------------------------

class TestExtractAllowedParticipants(unittest.TestCase):

    def test_extracts_all_four_categories(self):
        allowed = _extract_allowed_participants(SEBI_PLAN_JSON)
        self.assertIn("compliance officer", allowed)
        self.assertIn("sebi portal", allowed)
        self.assertIn("circular ingestion", allowed)
        self.assertIn("compliance data store", allowed)
        self.assertEqual(allowed["compliance officer"], "Compliance Officer")

    def test_empty_plan_returns_empty(self):
        allowed = _extract_allowed_participants("")
        self.assertEqual(allowed, {})

    def test_invalid_json_returns_empty(self):
        allowed = _extract_allowed_participants("not-json")
        self.assertEqual(allowed, {})

    def test_none_plan_returns_empty(self):
        allowed = _extract_allowed_participants(None)  # type: ignore[arg-type]
        self.assertEqual(allowed, {})


class TestCheckTraceability(unittest.TestCase):

    def setUp(self):
        self.allowed = _extract_allowed_participants(SEBI_PLAN_JSON)

    # ── Regression Test 1: Generator output passes traceability ──────────

    def test_valid_diagram_no_illegal_participants(self):
        """A diagram using only approved participants must pass the gate."""
        illegal = _check_traceability(VALID_SEBI_PUML, self.allowed)
        self.assertEqual(illegal, [], msg=f"Expected no illegal participants, got: {illegal}")

    # ── Regression Test 2: Scheduler rejected ────────────────────────────

    def test_scheduler_detected_as_illegal(self):
        """'Scheduler' is not in any approved plan — gate must reject it."""
        illegal = _check_traceability(SCHEDULER_PUML, self.allowed)
        self.assertIn("Scheduler", illegal, msg="Scheduler should be flagged as illegal.")

    # ── Regression Test 4: Workflow Engine rejected ───────────────────────

    def test_workflow_engine_detected_as_illegal(self):
        """'Workflow Engine' is not in any approved plan — gate must reject it."""
        illegal = _check_traceability(WORKFLOW_ENGINE_PUML, self.allowed)
        self.assertIn("Workflow Engine", illegal, msg="Workflow Engine should be flagged as illegal.")

    def test_no_plan_is_fail_open(self):
        """When allowed is empty (no plan), gate returns empty list (fail-open)."""
        illegal = _check_traceability(SCHEDULER_PUML, {})
        self.assertEqual(illegal, [])


class TestApplyLexicalFix(unittest.TestCase):

    def setUp(self):
        self.allowed = _extract_allowed_participants(SEBI_PLAN_JSON)

    # ── Regression Test 3: Compliance Reporting Service → Compliance Reporting ─

    def test_compliance_reporting_service_normalized(self):
        """'Compliance Reporting Service' is a superset of 'Compliance Reporting' — lexical fix."""
        fixed, applied, fixes = _apply_lexical_fix(COMPLIANCE_REPORTING_SERVICE_PUML, self.allowed)
        self.assertTrue(applied, "Lexical fix should have been applied.")
        self.assertTrue(
            any("Compliance Reporting Service" in f for f in fixes),
            f"Expected 'Compliance Reporting Service' in fix descriptions, got: {fixes}",
        )
        self.assertIn("Compliance Reporting", fixed)
        self.assertNotIn("Compliance Reporting Service", fixed)

    def test_no_change_when_all_approved(self):
        """A diagram with only approved participants should not be modified."""
        fixed, applied, fixes = _apply_lexical_fix(VALID_SEBI_PUML, self.allowed)
        self.assertFalse(applied, "No lexical fix should be needed for a valid diagram.")
        self.assertEqual(fixes, [])

    def test_no_plan_is_noop(self):
        """When allowed is empty the function is a noop."""
        fixed, applied, fixes = _apply_lexical_fix(SCHEDULER_PUML, {})
        self.assertFalse(applied)
        self.assertEqual(fixes, [])


class TestBuildStructuredFeedback(unittest.TestCase):

    def setUp(self):
        self.allowed = _extract_allowed_participants(SEBI_PLAN_JSON)

    def test_traceability_error_produces_structured_block(self):
        raw = "Non-traceable (invented) participants found: Scheduler"
        feedback = _build_structured_feedback(raw, self.allowed)
        self.assertIn("Validation Layer  : Architecture", feedback)
        self.assertIn("Traceability", feedback)
        self.assertIn("Compliance Reporting", feedback)  # approved participant listed
        self.assertIn("Required Fix", feedback)

    def test_graph_error_produces_structured_block(self):
        raw = "Graph Error: Duplicate relationship detected from 'A' to 'B'."
        feedback = _build_structured_feedback(raw, self.allowed)
        self.assertIn("Relationship Integrity", feedback)

    def test_syntax_error_passthrough(self):
        raw = "Syntax error on line 3: unexpected token"
        feedback = _build_structured_feedback(raw, self.allowed)
        self.assertIn("Syntax error", feedback)

    def test_empty_feedback(self):
        feedback = _build_structured_feedback("", self.allowed)
        self.assertIn("No specific", feedback)


# ---------------------------------------------------------------------------
# Integration Tests — full UMLRepairAgent.run() with mocked LLM
# ---------------------------------------------------------------------------

def _make_state(
    diagram_name: str,
    puml: str,
    plan_json: str,
    compiler_stderr: str,
    repair_attempts: int = 0,
) -> ForgeState:
    """Build a minimal ForgeState dict for repair agent testing.

    Uses cast() so the type checker accepts this partial dict without
    requiring every optional ForgeState key to be listed.
    """
    return cast(ForgeState, {
        "user_request": "Test SEBI compliance diagram",
        "current_stage": "uml_validator",
        "approval_status": "approved",
        "plantuml_diagrams": {diagram_name: puml},
        "plantuml_validation_report": {
            "diagram_results": [
                {
                    "diagram": diagram_name,
                    "valid": False,
                    "stderr": compiler_stderr,
                }
            ]
        },
        "diagram_execution_states": {
            diagram_name: {
                "diagram_id": diagram_name,
                "diagram_type": "sequence",
                "status": "generated",
                "attempt": 1,
                "generator_output": puml,
                "repair_attempts": repair_attempts,
                "diagram_plan": plan_json,
                "execution_time_ms": 1000,
                "llm_calls": 2,
            }
        },
        "metadata": {},
        "messages": [],
        "artifacts": {"uml": []},
        "approval_history": [],
        "reasoning_logs": [],
        "timeline_events": [],
        "execution_report": {},
        "generated_files": {},
    })


class TestRepairAgentTracebilityGate(unittest.TestCase):
    """Integration tests that verify the traceability gate prevents ValidationPipeline
    from ever seeing illegal participants."""

    def _make_mock_llm(self, repair_output: str) -> MagicMock:
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = repair_output
        mock_llm.invoke.return_value = mock_response
        return mock_llm

    # ── Regression Test 2: Scheduler rejected before ValidationPipeline ───

    def test_scheduler_in_repair_output_rejected_before_validation(self):
        """When the LLM produces a diagram with 'Scheduler', the traceability gate
        must reject it and ValidationPipeline must NEVER be called."""
        mock_llm = self._make_mock_llm(SCHEDULER_PUML)
        agent = UMLRepairAgent(llm=mock_llm)

        state = _make_state(
            diagram_name="sequence",
            puml=VALID_SEBI_PUML,
            plan_json=SEBI_PLAN_JSON,
            compiler_stderr="Non-traceable (invented) participants found: Scheduler",
        )

        with patch("agents.uml_generator.validators.ValidationPipeline") as mock_pipeline_cls:
            result = agent.run(state)
            mock_pipeline_cls.assert_not_called(), (
                "ValidationPipeline must NOT be instantiated when traceability gate rejects output."
            )

        # The repair output must not have been stored as the new diagram content
        diag_states = result.get("diagram_execution_states", {})
        self.assertEqual(
            diag_states.get("sequence", {}).get("architecture_status"),
            "failed",
        )
        # gate feedback should now be the stderr for the next cycle
        validation_report = state["plantuml_validation_report"]
        assert validation_report is not None
        gate_feedback = validation_report["diagram_results"][0]["stderr"]
        self.assertIn("Traceability Gate", gate_feedback)
        self.assertIn("Scheduler", gate_feedback)

    # ── Regression Test 4: Workflow Engine rejected immediately ───────────

    def test_workflow_engine_in_repair_output_rejected_immediately(self):
        """When the LLM produces a diagram with 'Workflow Engine', the traceability
        gate must reject it and ValidationPipeline must NOT be called."""
        mock_llm = self._make_mock_llm(WORKFLOW_ENGINE_PUML)
        agent = UMLRepairAgent(llm=mock_llm)

        state = _make_state(
            diagram_name="sequence",
            puml=VALID_SEBI_PUML,
            plan_json=SEBI_PLAN_JSON,
            compiler_stderr="Non-traceable (invented) participants found: Workflow Engine",
        )

        with patch("agents.uml_generator.validators.ValidationPipeline") as mock_pipeline_cls:
            result = agent.run(state)
            mock_pipeline_cls.assert_not_called()

        validation_report = state["plantuml_validation_report"]
        assert validation_report is not None
        gate_feedback = validation_report["diagram_results"][0]["stderr"]
        self.assertIn("Workflow Engine", gate_feedback)

    # ── Regression Test 3: Compliance Reporting Service normalized ────────

    def test_compliance_reporting_service_auto_normalized(self):
        """'Compliance Reporting Service' must be normalized to 'Compliance Reporting'
        by the lexical fix BEFORE the traceability gate runs, so no rejection occurs."""
        mock_llm = self._make_mock_llm(COMPLIANCE_REPORTING_SERVICE_PUML)
        agent = UMLRepairAgent(llm=mock_llm)

        state = _make_state(
            diagram_name="sequence",
            puml=VALID_SEBI_PUML,
            plan_json=SEBI_PLAN_JSON,
            compiler_stderr="Non-traceable (invented) participants found: Compliance Reporting Service",
        )

        mock_val_result = {
            "fixed_content": COMPLIANCE_REPORTING_SERVICE_PUML.replace(
                "Compliance Reporting Service", "Compliance Reporting"
            ),
            "pipeline_feedback": None,
            "uml_validation_metrics": {"grammar_score": 100, "architecture_score": 100},
            "syntax_valid": True,
            "grammar_status": "passed",
            "architecture_status": "passed",
            "business_flow_status": "passed",
        }

        with patch("agents.uml_generator.validators.ValidationPipeline") as mock_pipeline_cls:
            mock_pipeline_instance = MagicMock()
            mock_pipeline_instance.validate_diagram.return_value = mock_val_result
            mock_pipeline_cls.return_value = mock_pipeline_instance

            result = agent.run(state)

            # ValidationPipeline should have been called (lexical fix resolved the issue)
            mock_pipeline_cls.assert_called_once()

        # The stored diagram must not contain "Compliance Reporting Service"
        stored_puml = result.get("plantuml_diagrams", {}).get("sequence", "")
        self.assertNotIn("Compliance Reporting Service", stored_puml)

    # ── Regression Test 1: No new participants introduced ─────────────────

    def test_valid_repair_no_new_participants(self):
        """When the LLM produces a diagram using only approved participants,
        the repair succeeds and ValidationPipeline is called exactly once."""
        # Repair: fix a duplicate edge → output is still VALID_SEBI_PUML
        fixed_puml = VALID_SEBI_PUML  # same approved participants, fixed edge
        mock_llm = self._make_mock_llm(fixed_puml)
        agent = UMLRepairAgent(llm=mock_llm)

        # Start from a slightly different PUML to avoid duplicate-output detection
        original_puml_with_duplicate = VALID_SEBI_PUML + "\nCO -> CI : Upload Circular"

        state = _make_state(
            diagram_name="sequence",
            puml=original_puml_with_duplicate,
            plan_json=SEBI_PLAN_JSON,
            compiler_stderr='Graph Error: Duplicate relationship from "CO" to "CI".',
        )

        mock_val_result = {
            "fixed_content": fixed_puml,
            "pipeline_feedback": None,
            "uml_validation_metrics": {"grammar_score": 100, "architecture_score": 100},
            "syntax_valid": True,
            "grammar_status": "passed",
            "architecture_status": "passed",
            "business_flow_status": "passed",
        }

        with patch("agents.uml_generator.validators.ValidationPipeline") as mock_pipeline_cls:
            mock_pipeline_instance = MagicMock()
            mock_pipeline_instance.validate_diagram.return_value = mock_val_result
            mock_pipeline_cls.return_value = mock_pipeline_instance

            result = agent.run(state)

            mock_pipeline_cls.assert_called_once()

        # Verify no new participants in the final diagram
        allowed = _extract_allowed_participants(SEBI_PLAN_JSON)
        stored_puml = result.get("plantuml_diagrams", {}).get("sequence", "")
        illegal = _check_traceability(stored_puml, allowed)
        self.assertEqual(illegal, [], msg=f"No new participants should be introduced. Illegal: {illegal}")


if __name__ == "__main__":
    unittest.main()
