# Sequence Diagram Canonical Prompt

Generate a **Canonical Sequence Diagram JSON** capturing the primary happy-path business flow (max 10 participants, 15 messages). Participant layout & rendering are automated.

{context_block}

## Guidelines
- **Traceability**: Model primary interaction flow using exact entities from input context. Do not invent or split entities.
- **Participants**: Provide explicit ordered array `participants` containing element IDs from left to right.
- **Stable IDs**: Use lowercase identifiers (`actor_user`, `sys_payment`, `cap_order`, `db_order`). Relationships MUST use `source_id` and `target_id`.

## Output JSON Schema
Respond ONLY with valid JSON matching this schema:

```json
{
  "metadata": {"diagram_type": "sequence", "title": "<Title>", "description": "<Summary>"},
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
```

{few_shot}
