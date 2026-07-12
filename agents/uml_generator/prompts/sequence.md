# Sequence Diagram Prompt

## Objective

Generate a **Sequence Diagram** that captures the **primary business flow** of the system. This diagram will be used to communicate runtime behaviour in architecture reviews and onboarding documentation — precision and readability are essential.

{context_block}

## Diagram Requirements

### Scope & Focus

- Model **only the primary business flow** (the main success scenario / happy path).
- The diagram must contain a **maximum of 10 participants** and a **maximum of 20 messages**.
- Consolidate internal services behind a single façade participant.

### What to INCLUDE

- All primary actors (users, external systems) that initiate or receive the flow.
- Key domain services that participate in the core transaction.
- Synchronous calls (`->`) and responses (`-->`) with descriptive labels.
- Asynchronous messages (`->>`) where the architecture explicitly uses event-driven communication.

### Structural Constructs — Use Sparingly

- **`loop`**: Use ONLY when the business flow genuinely iterates.
- **`alt` / `else`**: Use ONLY when a critical business decision point must be shown.
- **`opt`**: Use ONLY for a clearly optional step that is architecturally significant.
- **`group`**: Use to label a logical phase of the flow.

### Notation Rules

- Declare participants explicitly.
- Order participants left-to-right following the natural flow.
- Use short, descriptive labels on every message arrow.
- Use `activate` / `deactivate` to show the lifeline of a service while it is processing.

{few_shot}
