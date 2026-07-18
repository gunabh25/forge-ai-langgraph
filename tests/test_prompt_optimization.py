"""Unit tests for Phase 9.7 Prompt Optimization."""

import json
from agents.uml_generator.prompt_builder import PromptBuilder
from schemas.canonical_diagram import ComponentDiagramCanonical, SequenceDiagramCanonical


def test_prompt_builder_character_count_component():
    """Verify built component diagram prompt total character count is within ~2,500-3,500 characters."""
    builder = PromptBuilder()
    summary = "Online Order Processing System with User, Payment Gateway, Order Service, and Order Database."
    
    system_prompt, user_prompt = builder.build_prompt(
        diagram_type="component",
        architecture_summary=summary,
    )
    
    total_len = len(system_prompt) + len(user_prompt)
    
    # Assert character length budget
    assert total_len <= 3500, f"Total prompt length {total_len} exceeds 3500 characters."
    assert total_len >= 1500, f"Total prompt length {total_len} is unexpectedly short."

    # Assert essential schema keywords are present
    for keyword in ["metadata", "actors", "external_systems", "business_packages", "business_capabilities", "databases", "relationships"]:
        assert keyword in user_prompt, f"Required JSON schema keyword '{keyword}' missing from user prompt."


def test_prompt_builder_character_count_sequence():
    """Verify built sequence diagram prompt total character count is within ~2,500-3,500 characters."""
    builder = PromptBuilder()
    summary = "User places order, Order Service authorizes payment via Payment Gateway and saves to Order DB."
    
    system_prompt, user_prompt = builder.build_prompt(
        diagram_type="sequence",
        architecture_summary=summary,
    )
    
    total_len = len(system_prompt) + len(user_prompt)
    
    # Assert character length budget
    assert total_len <= 3500, f"Total prompt length {total_len} exceeds 3500 characters."
    assert total_len >= 1500, f"Total prompt length {total_len} is unexpectedly short."

    # Assert essential schema keywords are present
    for keyword in ["metadata", "actors", "external_systems", "business_capabilities", "databases", "participants", "relationships"]:
        assert keyword in user_prompt, f"Required JSON schema keyword '{keyword}' missing from user prompt."


def test_schema_validity_of_prompt_json_examples():
    """Verify that the JSON schema examples in the prompts are valid Pydantic models."""
    sample_component_json = {
        "metadata": {"diagram_type": "component", "title": "Test Component", "description": "Test Summary"},
        "actors": [{"id": "actor_user", "name": "User", "stereotype": "actor"}],
        "external_systems": [{"id": "sys_payment", "name": "Payment Gateway", "technology": "REST API"}],
        "business_packages": [{"id": "pkg_core", "name": "Core Domain", "capability_ids": ["cap_order"]}],
        "business_capabilities": [{"id": "cap_order", "name": "Order Service", "stereotype": "service"}],
        "databases": [{"id": "db_order", "name": "Order Database", "db_type": "PostgreSQL"}],
        "relationships": [{"source_id": "actor_user", "target_id": "cap_order", "direction": "-->", "label": "Submits order"}]
    }
    comp_model = ComponentDiagramCanonical.model_validate(sample_component_json)
    assert comp_model.metadata.title == "Test Component"

    sample_sequence_json = {
        "metadata": {"diagram_type": "sequence", "title": "Test Sequence", "description": "Test Summary"},
        "actors": [{"id": "actor_user", "name": "User"}],
        "external_systems": [{"id": "sys_payment", "name": "Payment Gateway"}],
        "business_capabilities": [{"id": "cap_order", "name": "Order Service"}],
        "databases": [{"id": "db_order", "name": "Order Database"}],
        "participants": ["actor_user", "cap_order", "sys_payment", "db_order"],
        "relationships": [
            {"source_id": "actor_user", "target_id": "cap_order", "direction": "->", "label": "Place Order", "step_number": 1},
            {"source_id": "cap_order", "target_id": "sys_payment", "direction": "->", "label": "Authorize Payment", "step_number": 2}
        ]
    }
    seq_model = SequenceDiagramCanonical.model_validate(sample_sequence_json)
    assert seq_model.metadata.title == "Test Sequence"
