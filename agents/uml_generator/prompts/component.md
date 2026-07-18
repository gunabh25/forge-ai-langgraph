# Component Diagram Canonical Prompt

## Objective

Generate a **Canonical Component Diagram JSON** representation that captures the system's architectural structure at a glance.
The layout rendering will be handled deterministically by a compiler — you are responsible ONLY for architectural reasoning, component identification, and stable ID assignment.

{grammar_examples}

{context_block}

## Diagram Requirements & Traceability Guidelines

### Scope, Focus, and Traceability (CRITICAL)
- **Preserve Traceability**: The generated JSON must preserve the exact business capabilities, participants, and relationships produced by the architecture plan.
- **Never Alter Architecture**: You must NEVER rename business capabilities, merge business capabilities, split business capabilities, invent packages/services, remove relationships, or add unapproved relationships.
- Each capability must represent a **bounded context**, **domain service**, or **external integration** — not an implementation class.
- Target a **maximum of 8 components**. Group related capabilities into packages using `business_packages`.
- **Stable IDs**: Assign unique, stable lowercase identifiers to every element (e.g., `actor_customer`, `sys_payment_gateway`, `cap_order_service`, `db_order_db`, `pkg_core`). All relationships MUST reference entities strictly by `source_id` and `target_id`.

## Output Format Specification

Respond STRICTLY with raw JSON (or wrapped in ```json) matching the following Canonical Component Diagram schema. Do NOT output raw PlantUML code.

```json
{
  "metadata": {
    "diagram_type": "component",
    "title": "<System Component Architecture>",
    "description": "<Summary of component architecture>"
  },
  "actors": [
    {
      "id": "actor_customer",
      "name": "Customer",
      "stereotype": "actor"
    }
  ],
  "external_systems": [
    {
      "id": "sys_payment",
      "name": "Payment Gateway",
      "technology": "REST API"
    }
  ],
  "business_packages": [
    {
      "id": "pkg_order_domain",
      "name": "Order Management Domain",
      "capability_ids": ["cap_order_service"]
    }
  ],
  "business_capabilities": [
    {
      "id": "cap_order_service",
      "name": "Order Service",
      "stereotype": "service"
    }
  ],
  "databases": [
    {
      "id": "db_order_db",
      "name": "Order Database",
      "db_type": "PostgreSQL"
    }
  ],
  "relationships": [
    {
      "source_id": "actor_customer",
      "target_id": "cap_order_service",
      "direction": "-->",
      "label": "Places order"
    },
    {
      "source_id": "cap_order_service",
      "target_id": "db_order_db",
      "direction": "-->",
      "label": "Persists order"
    }
  ]
}
```

{few_shot}
