"""Phase 9 10-Scenario Enterprise Benchmark Suite.

Validates correctness, score cards, and byte-for-byte determinism across 10 enterprise domains.
"""

import json
import pytest
from schemas.canonical_diagram import ComponentDiagramCanonical, SequenceDiagramCanonical
from agents.uml_generator.plantuml_builder import PlantUMLBuilderFactory
from agents.uml_generator.validators import ArchitectureValidator
from agents.uml_generator.diagram_scorer import EnterpriseDiagramScorer, PRODUCTION_READINESS_THRESHOLD


BENCHMARK_SCENARIOS = {
    "compliance_monitoring": {
        "metadata": {"diagram_type": "component", "title": "SEBI Compliance Monitoring System"},
        "actors": [{"id": "actor_officer", "name": "Compliance Officer"}],
        "external_systems": [{"id": "sys_sebi", "name": "SEBI Portal", "technology": "REST API"}],
        "business_packages": [
            {"id": "pkg_core", "name": "Compliance Core", "capability_ids": ["cap_ingest", "cap_analysis"]}
        ],
        "business_capabilities": [
            {"id": "cap_ingest", "name": "Circular Ingestion"},
            {"id": "cap_analysis", "name": "Gap & Impact Analysis"}
        ],
        "databases": [{"id": "db_compliance", "name": "Compliance Database"}],
        "relationships": [
            {"source_id": "actor_officer", "target_id": "cap_analysis", "direction": "-->", "label": "Views Findings"},
            {"source_id": "sys_sebi", "target_id": "cap_ingest", "direction": "-->", "label": "Pulls Circulars"},
            {"source_id": "cap_ingest", "target_id": "cap_analysis", "direction": "-->", "label": "Feeds Clauses"},
            {"source_id": "cap_analysis", "target_id": "db_compliance", "direction": "-->", "label": "Persists Findings"}
        ]
    },
    "payment_gateway": {
        "metadata": {"diagram_type": "component", "title": "Payment Gateway Engine"},
        "actors": [{"id": "actor_customer", "name": "Customer"}],
        "external_systems": [{"id": "sys_visa", "name": "Visa Network", "technology": "ISO 8583"}],
        "business_packages": [
            {"id": "pkg_pay", "name": "Payment Core", "capability_ids": ["cap_auth", "cap_settlement"]}
        ],
        "business_capabilities": [
            {"id": "cap_auth", "name": "Transaction Authorizer"},
            {"id": "cap_settlement", "name": "Settlement Processor"}
        ],
        "databases": [{"id": "db_pay", "name": "Ledger DB"}],
        "relationships": [
            {"source_id": "actor_customer", "target_id": "cap_auth", "direction": "-->", "label": "Submits Payment"},
            {"source_id": "cap_auth", "target_id": "sys_visa", "direction": "-->", "label": "Authorizes"},
            {"source_id": "cap_auth", "target_id": "cap_settlement", "direction": "-->", "label": "Posts Transaction"},
            {"source_id": "cap_settlement", "target_id": "db_pay", "direction": "-->", "label": "Writes Ledger"}
        ]
    },
    "core_banking": {
        "metadata": {"diagram_type": "component", "title": "Core Banking Engine"},
        "actors": [{"id": "actor_teller", "name": "Bank Teller"}],
        "external_systems": [{"id": "sys_swift", "name": "SWIFT Network"}],
        "business_packages": [
            {"id": "pkg_accounts", "name": "Account Domain", "capability_ids": ["cap_accounts", "cap_transfers"]}
        ],
        "business_capabilities": [
            {"id": "cap_accounts", "name": "Account Management"},
            {"id": "cap_transfers", "name": "Fund Transfer Engine"}
        ],
        "databases": [{"id": "db_accounts", "name": "Accounts DB"}],
        "relationships": [
            {"source_id": "actor_teller", "target_id": "cap_accounts", "direction": "-->", "label": "Manage Accounts"},
            {"source_id": "cap_transfers", "target_id": "sys_swift", "direction": "-->", "label": "Send Wire"},
            {"source_id": "cap_accounts", "target_id": "cap_transfers", "direction": "-->", "label": "Initiate Transfer"},
            {"source_id": "cap_transfers", "target_id": "db_accounts", "direction": "-->", "label": "Update Balances"}
        ]
    },
    "enterprise_crm": {
        "metadata": {"diagram_type": "component", "title": "Enterprise CRM Platform"},
        "actors": [{"id": "actor_agent", "name": "Sales Rep"}],
        "external_systems": [{"id": "sys_email", "name": "SendGrid Email"}],
        "business_packages": [
            {"id": "pkg_sales", "name": "Sales Operations", "capability_ids": ["cap_lead", "cap_deal"]}
        ],
        "business_capabilities": [
            {"id": "cap_lead", "name": "Lead Management"},
            {"id": "cap_deal", "name": "Deal Pipeline Service"}
        ],
        "databases": [{"id": "db_crm", "name": "CRM Relational Store"}],
        "relationships": [
            {"source_id": "actor_agent", "target_id": "cap_lead", "direction": "-->", "label": "Log Lead"},
            {"source_id": "cap_lead", "target_id": "sys_email", "direction": "-->", "label": "Trigger Welcome Email"},
            {"source_id": "cap_lead", "target_id": "cap_deal", "direction": "-->", "label": "Convert to Deal"},
            {"source_id": "cap_deal", "target_id": "db_crm", "direction": "-->", "label": "Store Pipeline State"}
        ]
    },
    "inventory_supply_chain": {
        "metadata": {"diagram_type": "component", "title": "Supply Chain Inventory System"},
        "actors": [{"id": "actor_manager", "name": "Warehouse Manager"}],
        "external_systems": [{"id": "sys_rfid", "name": "RFID Scanner Gateway"}],
        "business_packages": [
            {"id": "pkg_inventory", "name": "Warehouse Operations", "capability_ids": ["cap_stock", "cap_reorder"]}
        ],
        "business_capabilities": [
            {"id": "cap_stock", "name": "Stock Tracking"},
            {"id": "cap_reorder", "name": "Automated Reorder Engine"}
        ],
        "databases": [{"id": "db_inventory", "name": "Inventory DB"}],
        "relationships": [
            {"source_id": "actor_manager", "target_id": "cap_stock", "direction": "-->", "label": "Inspect Stock"},
            {"source_id": "sys_rfid", "target_id": "cap_stock", "direction": "-->", "label": "Scan Items"},
            {"source_id": "cap_stock", "target_id": "cap_reorder", "direction": "-->", "label": "Check Thresholds"},
            {"source_id": "cap_reorder", "target_id": "db_inventory", "direction": "-->", "label": "Update Quantities"}
        ]
    },
    "hospital_management": {
        "metadata": {"diagram_type": "component", "title": "Hospital Management System"},
        "actors": [{"id": "actor_doctor", "name": "Doctor"}],
        "external_systems": [{"id": "sys_lab", "name": "External Lab System"}],
        "business_packages": [
            {"id": "pkg_clinical", "name": "Clinical Services", "capability_ids": ["cap_ehr", "cap_lab_orders"]}
        ],
        "business_capabilities": [
            {"id": "cap_ehr", "name": "EHR Management"},
            {"id": "cap_lab_orders", "name": "Lab Order Processing"}
        ],
        "databases": [{"id": "db_ehr", "name": "EHR Database"}],
        "relationships": [
            {"source_id": "actor_doctor", "target_id": "cap_ehr", "direction": "-->", "label": "Access Patient Chart"},
            {"source_id": "cap_ehr", "target_id": "cap_lab_orders", "direction": "-->", "label": "Order Test"},
            {"source_id": "cap_lab_orders", "target_id": "sys_lab", "direction": "-->", "label": "Transmit Order"},
            {"source_id": "cap_ehr", "target_id": "db_ehr", "direction": "-->", "label": "Save Clinical Notes"}
        ]
    },
    "hrms_payroll": {
        "metadata": {"diagram_type": "component", "title": "HRMS & Payroll System"},
        "actors": [{"id": "actor_hr", "name": "HR Specialist"}],
        "external_systems": [{"id": "sys_tax", "name": "Government Tax Portal"}],
        "business_packages": [
            {"id": "pkg_hr", "name": "HR Operations", "capability_ids": ["cap_employee", "cap_payroll"]}
        ],
        "business_capabilities": [
            {"id": "cap_employee", "name": "Employee Onboarding"},
            {"id": "cap_payroll", "name": "Payroll Engine"}
        ],
        "databases": [{"id": "db_hr", "name": "HR Data Store"}],
        "relationships": [
            {"source_id": "actor_hr", "target_id": "cap_employee", "direction": "-->", "label": "Onboard Employee"},
            {"source_id": "cap_employee", "target_id": "cap_payroll", "direction": "-->", "label": "Configure Salary"},
            {"source_id": "cap_payroll", "target_id": "sys_tax", "direction": "-->", "label": "Submit Tax Withholdings"},
            {"source_id": "cap_payroll", "target_id": "db_hr", "direction": "-->", "label": "Record Pay Slips"}
        ]
    },
    "insurance_claims": {
        "metadata": {"diagram_type": "component", "title": "Insurance Claims Processing"},
        "actors": [{"id": "actor_claimant", "name": "Policy Holder"}],
        "external_systems": [{"id": "sys_claims_adj", "name": "Third-Party Adjuster Service"}],
        "business_packages": [
            {"id": "pkg_claims", "name": "Claims Management", "capability_ids": ["cap_fnol", "cap_adjudication"]}
        ],
        "business_capabilities": [
            {"id": "cap_fnol", "name": "First Notice of Loss"},
            {"id": "cap_adjudication", "name": "Claims Adjudication Engine"}
        ],
        "databases": [{"id": "db_claims", "name": "Claims Repository"}],
        "relationships": [
            {"source_id": "actor_claimant", "target_id": "cap_fnol", "direction": "-->", "label": "File Claim"},
            {"source_id": "cap_fnol", "target_id": "cap_adjudication", "direction": "-->", "label": "Submit for Review"},
            {"source_id": "cap_adjudication", "target_id": "sys_claims_adj", "direction": "-->", "label": "Request Inspection"},
            {"source_id": "cap_adjudication", "target_id": "db_claims", "direction": "-->", "label": "Update Claim Status"}
        ]
    },
    "ecommerce_platform": {
        "metadata": {"diagram_type": "component", "title": "E-Commerce Checkout & Fulfillment"},
        "actors": [{"id": "actor_buyer", "name": "Shopper"}],
        "external_systems": [{"id": "sys_stripe", "name": "Stripe Payments"}],
        "business_packages": [
            {"id": "pkg_cart", "name": "Cart & Checkout", "capability_ids": ["cap_cart", "cap_order_proc"]}
        ],
        "business_capabilities": [
            {"id": "cap_cart", "name": "Shopping Cart Service"},
            {"id": "cap_order_proc", "name": "Order Processor"}
        ],
        "databases": [{"id": "db_orders", "name": "Orders Database"}],
        "relationships": [
            {"source_id": "actor_buyer", "target_id": "cap_cart", "direction": "-->", "label": "Checkout Cart"},
            {"source_id": "cap_cart", "target_id": "cap_order_proc", "direction": "-->", "label": "Create Order"},
            {"source_id": "cap_order_proc", "target_id": "sys_stripe", "direction": "-->", "label": "Process Payment"},
            {"source_id": "cap_order_proc", "target_id": "db_orders", "direction": "-->", "label": "Persist Order"}
        ]
    },
    "microservices_infrastructure": {
        "metadata": {"diagram_type": "component", "title": "Microservices Observability Infrastructure"},
        "actors": [{"id": "actor_devops", "name": "DevOps Engineer"}],
        "external_systems": [{"id": "sys_pagerduty", "name": "PagerDuty Incident Platform"}],
        "business_packages": [
            {"id": "pkg_obs", "name": "Telemetry Pipeline", "capability_ids": ["cap_metrics", "cap_alerting"]}
        ],
        "business_capabilities": [
            {"id": "cap_metrics", "name": "Metrics Ingestion Service"},
            {"id": "cap_alerting", "name": "Alerting Engine"}
        ],
        "databases": [{"id": "db_ts", "name": "Time-Series DB (Prometheus)"}],
        "relationships": [
            {"source_id": "actor_devops", "target_id": "cap_alerting", "direction": "-->", "label": "Configure Rules"},
            {"source_id": "cap_metrics", "target_id": "db_ts", "direction": "-->", "label": "Write Metrics"},
            {"source_id": "cap_alerting", "target_id": "db_ts", "direction": "-->", "label": "Evaluate Metrics"},
            {"source_id": "cap_alerting", "target_id": "sys_pagerduty", "direction": "-->", "label": "Trigger Alert"}
        ]
    }
}


@pytest.mark.parametrize("scenario_id,scenario_data", list(BENCHMARK_SCENARIOS.items()))
def test_benchmark_scenarios_validation_and_scoring(scenario_id, scenario_data):
    """Test validation and scoring for all 10 enterprise benchmark scenarios."""
    canonical = ComponentDiagramCanonical.model_validate(scenario_data)

    builder = PlantUMLBuilderFactory.get_builder("component")
    puml = builder.build(canonical)

    plan_json = json.dumps({
        "actors": [a["name"] for a in scenario_data["actors"]],
        "external_systems": [e["name"] for e in scenario_data["external_systems"]],
        "major_components": [c["name"] for c in scenario_data["business_capabilities"]],
        "major_data_stores": [d["name"] for d in scenario_data["databases"]],
    })

    validator = ArchitectureValidator()
    val_res = validator.validate("component", plan_json, puml)

    assert val_res["passed"] is True
    assert val_res["score"] == 100

    score_card = EnterpriseDiagramScorer.evaluate(
        diagram_type="component",
        plantuml_content=puml,
        grammar_res={"passed": True, "score": 100},
        arch_res=val_res,
        flow_res={"passed": True, "score": 100},
    )

    assert score_card.overall_score >= PRODUCTION_READINESS_THRESHOLD
    assert score_card.is_production_ready is True


def test_100_consecutive_runs_determinism():
    """Verify 100 consecutive baseline runs produce 100% byte-identical PlantUML strings."""
    data = BENCHMARK_SCENARIOS["compliance_monitoring"]
    canonical = ComponentDiagramCanonical.model_validate(data)
    builder = PlantUMLBuilderFactory.get_builder("component")

    reference_puml = builder.build(canonical)
    for _ in range(100):
        current_puml = builder.build(canonical)
        assert current_puml == reference_puml
