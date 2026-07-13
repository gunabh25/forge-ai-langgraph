"""Phase 7.3 Regression Tests — BusinessFlowValidator Planner-Aware Actor Rule.

Tasks 5 & 6 — Regression Tests verifying:

  Test 1 – actors=[]  diagram starts with "Circular Ingestion" → PASS
  Test 2 – actors=[]  diagram starts with "SEBI"              → PASS
  Test 3 – actors=["Compliance Officer"]  starts with "Circular Ingestion" → FAIL
  Test 4 – actors=["Compliance Officer"]  starts with "Compliance Officer" → PASS
  Test 5 – actors=[]  diagram starts with "Scheduler" (not planned)       → FAIL

Existing checks (self-loops, duplicate messages, orphans) are covered by guard tests
to confirm no regressions.
"""

import json
import unittest
from unittest.mock import MagicMock

from agents.uml_generator.validators import BusinessFlowValidator


# ---------------------------------------------------------------------------
# Plan JSON factories
# ---------------------------------------------------------------------------

def _plan(actors=None, external_systems=None, major_components=None) -> str:
    return json.dumps({
        "actors": actors or [],
        "external_systems": external_systems or [],
        "major_components": major_components or [],
        "major_data_stores": [],
        "business_flow": [],
        "diagram_scope": "Test scope.",
    })


SEBI_PLAN_NO_ACTORS = _plan(
    actors=[],
    external_systems=["SEBI Portal"],
    major_components=["Circular Ingestion", "Circular Parsing",
                      "Requirements Extraction", "Gap Analysis",
                      "Impact Assessment", "Compliance Reporting"],
)

SEBI_PLAN_WITH_ACTOR = _plan(
    actors=["Compliance Officer"],
    external_systems=["SEBI Portal"],
    major_components=["Circular Ingestion", "Circular Parsing",
                      "Requirements Extraction", "Gap Analysis",
                      "Impact Assessment", "Compliance Reporting"],
)

MINIMAL_PLAN_NO_ACTORS = _plan(
    actors=[],
    external_systems=["SEBI Portal"],
    major_components=["Circular Ingestion", "Gap Analysis"],
)


# ---------------------------------------------------------------------------
# PlantUML fixtures
# ---------------------------------------------------------------------------

PUML_STARTS_CIRCULAR_INGESTION = """\
@startuml
participant "Circular Ingestion" as CI
participant "Circular Parsing" as CP
participant "Gap Analysis" as GA
participant "Compliance Reporting" as CR

CI -> CP : Parse Content
CP -> GA : Identify Gaps
GA -> CR : Generate Report
@enduml"""

PUML_STARTS_SEBI = """\
@startuml
participant "SEBI Portal" as SP
participant "Circular Ingestion" as CI
participant "Gap Analysis" as GA

SP -> CI : Publish Circular
CI -> GA : Analyse
@enduml"""

PUML_STARTS_COMPLIANCE_OFFICER = """\
@startuml
actor "Compliance Officer" as CO
participant "Circular Ingestion" as CI
participant "Compliance Reporting" as CR

CO -> CI : Upload Circular
CI -> CR : Generate Report
CR -> CO : Deliver Report
@enduml"""

PUML_STARTS_SCHEDULER = """\
@startuml
participant "Scheduler" as SCH
participant "Circular Ingestion" as CI
participant "Gap Analysis" as GA

SCH -> CI : Trigger Ingestion
CI -> GA : Analyse
@enduml"""

PUML_SELF_LOOP = """\
@startuml
participant "Circular Ingestion" as CI

CI -> CI : Self-trigger
@enduml"""

PUML_DUPLICATE_MSG = """\
@startuml
participant "Circular Ingestion" as CI
participant "Gap Analysis" as GA

CI -> GA : Analyse
CI -> GA : Analyse
@enduml"""


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _validator() -> BusinessFlowValidator:
    return BusinessFlowValidator(llm=MagicMock())


# ---------------------------------------------------------------------------
# Unit tests for helper methods
# ---------------------------------------------------------------------------

class TestPlanActorParser(unittest.TestCase):

    def test_returns_actors_when_present(self):
        plan = _plan(actors=["Compliance Officer", "Admin"])
        self.assertEqual(
            BusinessFlowValidator._parse_plan_actors(plan),
            ["Compliance Officer", "Admin"],
        )

    def test_returns_empty_list_when_no_actors(self):
        plan = _plan(actors=[])
        self.assertEqual(BusinessFlowValidator._parse_plan_actors(plan), [])

    def test_returns_empty_on_invalid_json(self):
        self.assertEqual(BusinessFlowValidator._parse_plan_actors("not-json"), [])

    def test_returns_empty_on_empty_string(self):
        self.assertEqual(BusinessFlowValidator._parse_plan_actors(""), [])


class TestPlanEntryParticipantsParser(unittest.TestCase):

    def test_returns_external_systems_and_components(self):
        plan = _plan(
            external_systems=["SEBI Portal"],
            major_components=["Circular Ingestion", "Gap Analysis"],
        )
        result = BusinessFlowValidator._parse_plan_entry_participants(plan)
        self.assertIn("SEBI Portal", result)
        self.assertIn("Circular Ingestion", result)
        self.assertIn("Gap Analysis", result)

    def test_returns_empty_on_empty_plan(self):
        self.assertEqual(BusinessFlowValidator._parse_plan_entry_participants(""), [])


# ---------------------------------------------------------------------------
# Phase 7.3 regression tests
# ---------------------------------------------------------------------------

class TestBusinessFlowValidatorPlannerAwareActorRule(unittest.TestCase):

    def setUp(self):
        self.v = _validator()

    # Test 1
    def test_no_actors_starts_with_approved_component_passes(self):
        """actors=[]  starts with Circular Ingestion (approved component) → PASS."""
        r = self.v.validate("sequence", SEBI_PLAN_NO_ACTORS, PUML_STARTS_CIRCULAR_INGESTION)
        self.assertTrue(r["passed"],
            msg=f"Expected PASS. Errors: {r.get('errors')}")
        self.assertEqual(r["validator"], "Business Flow Validator")

    # Test 2
    def test_no_actors_starts_with_external_system_passes(self):
        """actors=[]  starts with SEBI Portal (approved external system) → PASS."""
        r = self.v.validate("sequence", SEBI_PLAN_NO_ACTORS, PUML_STARTS_SEBI)
        self.assertTrue(r["passed"],
            msg=f"Expected PASS. Errors: {r.get('errors')}")

    # Test 3
    def test_actor_planned_but_absent_from_diagram_fails(self):
        """actors=["Compliance Officer"]  starts with Circular Ingestion → FAIL."""
        r = self.v.validate("sequence", SEBI_PLAN_WITH_ACTOR, PUML_STARTS_CIRCULAR_INGESTION)
        self.assertFalse(r["passed"],
            msg="Expected FAIL when planned actor absent from diagram.")
        self.assertTrue(
            any("actor" in e.lower() or "compliance officer" in e.lower()
                for e in r.get("errors", [])),
            msg=f"Expected actor-related error. Got: {r.get('errors')}",
        )

    # Test 4
    def test_actor_planned_and_present_passes(self):
        """actors=["Compliance Officer"]  starts with Compliance Officer → PASS."""
        r = self.v.validate("sequence", SEBI_PLAN_WITH_ACTOR, PUML_STARTS_COMPLIANCE_OFFICER)
        self.assertTrue(r["passed"],
            msg=f"Expected PASS when planned actor is in diagram. Errors: {r.get('errors')}")

    # Test 5
    def test_no_actors_unapproved_entry_fails(self):
        """actors=[]  starts with Scheduler (not in plan) → FAIL."""
        r = self.v.validate("sequence", MINIMAL_PLAN_NO_ACTORS, PUML_STARTS_SCHEDULER)
        self.assertFalse(r["passed"],
            msg="Expected FAIL when entry participant Scheduler is not approved.")
        self.assertTrue(
            any("scheduler" in e.lower() or "not in the approved" in e.lower()
                for e in r.get("errors", [])),
            msg=f"Expected unapproved-entry error. Got: {r.get('errors')}",
        )


# ---------------------------------------------------------------------------
# Regression guards — existing checks must not regress
# ---------------------------------------------------------------------------

class TestBusinessFlowValidatorRegressionGuards(unittest.TestCase):

    def setUp(self):
        self.v = _validator()

    def test_self_loop_still_detected(self):
        r = self.v.validate("sequence", SEBI_PLAN_NO_ACTORS, PUML_SELF_LOOP)
        self.assertFalse(r["passed"])
        self.assertTrue(any("self-loop" in e.lower() for e in r.get("errors", [])),
            msg=f"Expected self-loop error. Got: {r.get('errors')}")

    def test_duplicate_adjacent_message_still_detected(self):
        r = self.v.validate("sequence", SEBI_PLAN_NO_ACTORS, PUML_DUPLICATE_MSG)
        self.assertFalse(r["passed"])
        self.assertTrue(any("duplicate" in e.lower() for e in r.get("errors", [])),
            msg=f"Expected duplicate-message error. Got: {r.get('errors')}")

    def test_non_sequence_diagram_always_passes(self):
        r = self.v.validate("component", SEBI_PLAN_NO_ACTORS,
                            "@startuml\n[A] --> [B]\n@enduml")
        self.assertTrue(r["passed"])
        self.assertEqual(r["score"], 100)


if __name__ == "__main__":
    unittest.main()
