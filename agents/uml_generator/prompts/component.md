# Component Diagram Prompt

## Objective

Generate a **high-level Component Diagram** that communicates the system's architectural structure at a glance. This diagram will be used in architecture review sessions and technical documentation.

{context_block}

## Diagram Requirements

### Scope & Focus

- Show ONLY architecturally significant services, modules, and external systems.
- Each component must represent a **bounded context**, **domain service**, or **external integration** — not an implementation class.
- Target a **maximum of 8 components**. Group related capabilities if necessary.
- Minimize edge crossings to improve readability.

### What to INCLUDE

- Core business services and external integrations.
- Clear dependency arrows (`-->`) showing the direction of invocation or data flow.
- Groupings (`package`, `cloud`, `node`) to convey deployment or domain boundaries.
- Brief stereotypes (e.g. `<<service>>`, `<<external>>`, `<<datastore>>`).

### Notation Rules

- Use `[Component Name]` notation for components.
- Use `database` keyword for persistent data stores.
- Label arrows with the interaction verb or protocol (e.g. `-- "REST" -->`).

{few_shot}
