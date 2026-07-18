# Component Diagram Canonical Prompt

Generate a **Canonical Component Diagram JSON** capturing high-level architectural structure (max 8 components). Layout/rendering is automated — focus ONLY on component identification, package grouping, and relationship mapping.

{context_block}

## Guidelines
- **Traceability**: Preserve exact entities and relationships from input context. Do not invent, rename, merge, or split business capabilities.
- **Stable IDs**: Use lowercase identifiers (`actor_user`, `sys_payment`, `cap_order`, `db_order`, `pkg_core`). Relationships MUST use `source_id` and `target_id`.
- **Domain Focus**: Bounded contexts & domain services only. Avoid implementation leakage.

## Output JSON Schema
Respond ONLY with valid JSON matching this schema:

```json
{
  "metadata": {"diagram_type": "component", "title": "<Title>", "description": "<Summary>"},
  "actors": [{"id": "actor_user", "name": "User", "stereotype": "actor"}],
  "external_systems": [{"id": "sys_payment", "name": "Payment Gateway", "technology": "REST API"}],
  "business_packages": [{"id": "pkg_core", "name": "Core Domain", "capability_ids": ["cap_order"]}],
  "business_capabilities": [{"id": "cap_order", "name": "Order Service", "stereotype": "service"}],
  "databases": [{"id": "db_order", "name": "Order Database", "db_type": "PostgreSQL"}],
  "relationships": [{"source_id": "actor_user", "target_id": "cap_order", "direction": "-->", "label": "Submits order"}]
}
```

{few_shot}
