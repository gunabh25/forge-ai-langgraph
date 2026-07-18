# Sequence Diagram Canonical Prompt

## Objective

Generate a **Canonical Sequence Diagram JSON** representation capturing the **primary business flow** of the system.
The layout rendering and participant ordering will be handled deterministically by a compiler — you are responsible ONLY for architectural reasoning, participant identification, stable ID assignment, and flow sequence steps.

{grammar_examples}

{context_block}

## Diagram Requirements & Traceability Guidelines

### Scope, Focus, and Traceability (CRITICAL)
- **Preserve Traceability**: The generated JSON must preserve the exact business capabilities, participants, and relationships produced by the architecture plan.
- **Never Alter Architecture**: You must NEVER rename business capabilities, merge business capabilities, split business capabilities, invent participants, remove relationships, or add unapproved relationships.
- Model **only the primary business flow** (the main success scenario / happy path).
- The diagram must contain a **maximum of 10 participants** and a **maximum of 15 meaningful messages**.
- **Stable IDs & Participants**: Assign unique, stable lowercase identifiers to every element (e.g., `actor_customer`, `sys_payment_gateway`, `cap_order_service`, `db_order_db`). Provide an explicit ordered array `participants` containing element IDs from left to right.
- All relationships MUST reference entities strictly by `source_id` and `target_id`.

## Output Format Specification

Respond STRICTLY with raw JSON (or wrapped in ```json) matching the following Canonical Sequence Diagram schema. Do NOT output raw PlantUML code.

```json
{
  "metadata": {
    "diagram_type": "sequence",
    "title": "<Primary Workflow Sequence>",
    "description": "<Summary of sequence flow>"
  },
  "actors": [
    {
      "id": "actor_customer",
      "name": "Customer"
    }
  ],
  "external_systems": [
    {
      "id": "sys_payment",
      "name": "Payment Gateway"
    }
  ],
  "business_capabilities": [
    {
      "id": "cap_order_service",
      "name": "Order Service"
    }
  ],
  "databases": [
    {
      "id": "db_order_db",
      "name": "Order Database"
    }
  ],
  "participants": [
    "actor_customer",
    "cap_order_service",
    "sys_payment",
    "db_order_db"
  ],
  "relationships": [
    {
      "source_id": "actor_customer",
      "target_id": "cap_order_service",
      "direction": "->",
      "label": "Place Order",
      "step_number": 1
    },
    {
      "source_id": "cap_order_service",
      "target_id": "sys_payment",
      "direction": "->",
      "label": "Authorize Payment",
      "step_number": 2
    },
    {
      "source_id": "cap_order_service",
      "target_id": "db_order_db",
      "direction": "->",
      "label": "Store Order Record",
      "step_number": 3
    }
  ]
}
```

{few_shot}
