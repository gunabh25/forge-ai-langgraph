# Sequence Diagram Prompt

## Objective

Generate a **Sequence Diagram** that captures the **primary business flow** of the system. This diagram will be used to communicate runtime behaviour in architecture reviews and onboarding documentation — precision and readability are essential.

{grammar_examples}

{context_block}

## Diagram Requirements

### Scope & Focus

- Model **only the primary business flow** (the main success scenario / happy path).
- Prefer a clean left-to-right business flow: Actor → Entry Capability → Business Capability → External System → Customer Notification.
- The diagram must contain a **maximum of 10 participants** and a **maximum of 15 meaningful messages**.
- Every participant should actively contribute to the business flow. Avoid participants that only send or receive one trivial message. Merge responsibilities where appropriate.
- Avoid participants talking back and forth unnecessarily.
- Avoid unnecessary acknowledgement messages. Focus on fewer but more meaningful interactions.

### What to INCLUDE

- All primary actors (users, external systems) that initiate or receive the flow.
- Key domain services that participate in the core transaction.
- Synchronous calls (`->`) and responses (`-->`) with **business-centric descriptive labels**. Labels must describe actions (e.g., "Submit Claim", "Validate Eligibility", "Process Payment" — NEVER generic terms like "Request", "Response", "Call API", "Data").
- Asynchronous messages (`->>`) where the architecture explicitly uses event-driven communication.

### Traceability (CRITICAL)

- Every participant must be directly traceable to the approved Diagram Plan.
- Allowed participants: planned business capabilities, approved aliases, actors, external systems, and planned data stores.
- Do NOT invent: new services, business domains, middleware, orchestration layers, backend services, or generic processing components.
- If a participant is not present in the planning output, do not generate it.

### Structural Constructs — Use Sparingly

- **`loop`**: Use ONLY when the business flow genuinely iterates.
- **`alt` / `else`**: Use ONLY when a critical business decision point must be shown.
- **`opt`**: Use ONLY for a clearly optional step that is architecturally significant.
- **`group`**: Use to label a logical phase of the flow.

### Notation Rules

- Declare participants explicitly.
- Order participants left-to-right following the natural flow.
- Use short, descriptive business-action labels on every message arrow.
- Use `activate` / `deactivate` only when they improve readability. Avoid excessive nesting so the diagram remains visually clean.

{few_shot}
