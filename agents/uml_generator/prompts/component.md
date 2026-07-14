# Component Diagram Prompt

## Objective

Generate a **high-level Component Diagram** that communicates the system's architectural structure at a glance. This diagram will be used in architecture review sessions and technical documentation.

{grammar_examples}

{context_block}

## Diagram Requirements & Human Readability Guidelines

### Scope, Focus, and Traceability (CRITICAL)
- **Preserve Traceability**: The generated PlantUML must preserve the exact business capabilities, participants, and relationships produced by the architecture plan.
- **Never Alter Architecture**: You must NEVER rename business capabilities (except for omitting redundant suffixes as allowed below), merge business capabilities, split business capabilities, invent packages/services, remove relationships, or add relationships.
- Show ONLY architecturally significant services, modules, and external systems.
- Each component must represent a **bounded context**, **domain service**, or **external integration** — not an implementation class.
- Target a **maximum of 8 components**. Group related capabilities into packages if necessary.
- **Optimize for Human Understanding**: Never optimize for fewer lines of code. Optimize for faster human understanding. Allow generous spacing and whitespace.

### Component Labels & Naming
- **Concise Presentation Labels**: Prefer concise labels. Do not abbreviate business terminology (e.g. use "Impact Assessment", not "Impact Assess."). Maintain clarity over brevity.
- **Remove Suffix Redundancies**: Preserve the business capability name exactly, but omit redundant suffixes such as `Service`, `Component`, `Module`, `System`, `Manager`, or `Engine` where doing so improves readability without changing the underlying meaning.

### Component Placement & Layer Layout
- **Flexible Component Layout**: Preferred layout (not mandatory):
  - **Actors** -> Place on the Left.
  - **Business Capabilities** -> Place in the Center.
  - **External Systems** -> Place on the Left or Right depending on interaction (choose whichever minimizes edge crossings).
  - **Databases** -> Place at the Bottom.
  - Let the layout engine select whichever layout minimizes edge crossings for that specific architecture.
- **Directional Flexibility**: Do not force a single direction (`left to right direction` vs. default top-to-bottom) universally. Select the layout direction that minimizes edge crossings and produces the most readable layout.
  - Prefer **left-to-right** (`left to right direction`) for pipeline architectures.
  - Prefer **top-to-bottom** (default PlantUML ranksep layout) for workflow architectures.

### Business Domain Clustering & Package Guidelines
- **Domain Clustering**: Before generating, cluster business capabilities into logical domains representing actual business responsibilities (e.g. `Document Processing`, `Assessment`, `Compliance`, `Reporting`).
  - Maximize internal relationships (cohesion) within packages and minimize relationships crossing package boundaries (coupling).
  - Do not create arbitrary package names (e.g. `Package 1`, `Services`, `Miscellaneous`).
  - Create packages only when they improve readability. If the diagram contains fewer than six business components, do not introduce packages unnecessarily.
  - Preferred package count: **2-4 packages**. Avoid deeply nested packages or package-inside-package layouts. Each package should contain **2-4 related components**.

### Database & Actor Placement
- **Actor Unity**: Actors should appear only once.
- **Dedicated Data Layer**: Databases must appear in a dedicated data layer at the bottom. Never scatter databases throughout the diagram. Align related databases horizontally and place them directly beneath the business package or service that owns them.

### Relationship Readability
- Minimize edge crossings, avoid zig-zag arrows, and avoid unnecessary diagonal edges.
- Keep arrows orthogonal whenever PlantUML supports it. Use directional arrows (e.g., `-right->`, `-left->`, `-down->`, `-up->`) to guide layouts if it reduces crossings.
- Reduce many-to-one edge convergence.

### Default PlantUML Styling
Use the following skinparams as defaults unless they would reduce readability for the current diagram (giving the model flexibility to adjust spacing if the layout requires it):
```plantuml
skinparam shadowing false
skinparam componentStyle rectangle
skinparam packageStyle rectangle
skinparam linetype ortho
skinparam dpi 180
skinparam ArrowThickness 2
skinparam nodesep 70
skinparam ranksep 90
skinparam defaultFontSize 14
skinparam wrapWidth 180
```
Do not introduce custom color themes or aggressive background coloring. Maintain a clean, professional, enterprise-grade appearance.

### Internal Layout Pass & Readability Self-Check
Before generating the final PlantUML block, you must internally perform a layout planning step and a readability self-check:
1. **Layout Planning Step**:
   - Determine Business domains and package groupings (maximizing cohesion, minimizing coupling).
   - Determine layer ordering (Actors, Business capabilities, External systems, Databases).
   - Determine layout direction (left-to-right vs. top-to-bottom).
   - Determine horizontal/vertical relationship routing to minimize crossings.
2. **Readability Self-Check**:
   - ✓ Can the architecture be understood within 10 seconds?
   - ✓ Are related capabilities grouped?
   - ✓ Are actors clearly separated and unique?
   - ✓ Are databases aligned at the bottom under their owner?
   - ✓ Are edge crossings minimized and arrows orthogonal?
   - ✓ Is whitespace sufficient?
   - ✓ Are labels concise without abbreviations or redundant suffixes?
   - ✓ Does the diagram resemble enterprise architecture documentation?

Only emit the final PlantUML block once all checks pass. Do not expose your layout planning or self-check reasoning outside the `@startuml` ... `@enduml` block.

{few_shot}
