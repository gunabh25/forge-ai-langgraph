# Sequence Diagram Prompt

## Objective

Generate a **Sequence Diagram** that captures the **primary business flow** of the system. This diagram will be used to communicate runtime behaviour in architecture reviews and onboarding documentation — precision and readability are essential.

{grammar_examples}

{context_block}

## Diagram Requirements & Human Readability Guidelines

### Scope, Focus, and Traceability (CRITICAL)
- **Preserve Traceability**: The generated PlantUML must preserve the exact business capabilities, participants, and relationships produced by the architecture plan.
- **Never Alter Architecture**: You must NEVER rename business capabilities (except for omitting redundant suffixes as allowed below), merge business capabilities, split business capabilities, invent packages/services, remove relationships, or add relationships.
- Model **only the primary business flow** (the main success scenario / happy path).
- The diagram must contain a **maximum of 10 participants** and a **maximum of 15 meaningful messages**.
- Every participant should actively contribute to the business flow. Avoid participants that only send or receive one trivial message.
- **Optimize for Human Understanding**: Never optimize for fewer lines of code. Optimize for faster human understanding.

### Participant Labels & Naming
- **Concise Presentation Labels**: Prefer concise labels. Do not abbreviate business terminology (e.g. use "Impact Assessment", not "Impact Assess."). Maintain clarity over brevity.
- **Remove Suffix Redundancies**: Preserve the business capability name exactly, but omit redundant suffixes such as `Service`, `Component`, `Module`, `System`, `Manager`, or `Engine` where doing so improves readability without changing the underlying meaning.

### Flow Layout & Readability (Task 11)
- **Left-to-Right Flow**: Sequence participants must be ordered from left to right following the natural direction of the workflow. Order participants left-to-right explicitly.
- **Limit Participants**: Restrict participants to meaningful business entities.
- **No Unnecessary Acks**: Avoid redundant acknowledgement messages or repeated response arrows (e.g., `Service --> Actor: Ack/OK` or repeated return arrows unless critical to understanding).
- **Logical Groupings**: Group logical steps using `group`, `alt`, or `opt` only where they significantly improve human understanding. Keep message labels concise.
- **Balanced Aspect Ratio**: Avoid excessively wide sequence diagrams. Ensure it fits comfortably on a laptop screen.

### Default PlantUML Styling
Use the following skinparams as defaults unless they would reduce readability for the current diagram (giving the model flexibility to adjust spacing if the layout requires it):
```plantuml
skinparam shadowing false
skinparam linetype ortho
skinparam dpi 180
skinparam ArrowThickness 2
skinparam defaultFontSize 14
skinparam wrapWidth 180
```
Do not introduce custom color themes or aggressive background coloring. Maintain a clean, professional, enterprise-grade appearance.

### Internal Layout Pass & Readability Self-Check
Before generating the final PlantUML block, you must internally perform a layout planning step and a readability self-check:
1. **Layout Planning Step**:
   - Determine sequence participants and order them logically from left to right (Actors on left, core services in center, external/data stores towards the right).
   - Plan flow messages to ensure left-to-right progress.
   - Plan logical grouping blocks (`group`, `alt`, `opt`) for readability.
2. **Readability Self-Check**:
   - ✓ Can the flow be understood within 10 seconds?
   - ✓ Are actors separated from services?
   - ✓ Are unnecessary response/ack arrows avoided?
   - ✓ Is the diagram width balanced (not excessively wide)?
   - ✓ Are labels concise without abbreviations or redundant suffixes?
   - ✓ Does the diagram resemble enterprise architecture documentation?

Only emit the final PlantUML block once all checks pass. Do not expose your layout planning or self-check reasoning outside the `@startuml` ... `@enduml` block.

{few_shot}
