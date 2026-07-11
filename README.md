<div align="center">
  <img src="https://via.placeholder.com/150x150.png?text=ForgeAI+Logo" alt="ForgeAI Logo" width="150" height="150" />
  <h1>ForgeAI</h1>
  <p><strong>Enterprise-Grade Dynamic Workflow Orchestrator & Autonomous Software Engineering Platform</strong></p>

  <p>
    <a href="https://github.com/your-org/forge-ai-langgraph/releases"><img src="https://img.shields.io/github/v/release/your-org/forge-ai-langgraph" alt="Release" /></a>
    <a href="https://github.com/your-org/forge-ai-langgraph/actions"><img src="https://img.shields.io/github/actions/workflow/status/your-org/forge-ai-langgraph/ci.yml" alt="Build Status" /></a>
    <a href="https://codecov.io/gh/your-org/forge-ai-langgraph"><img src="https://img.shields.io/codecov/c/github/your-org/forge-ai-langgraph" alt="Coverage" /></a>
    <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License" /></a>
  </p>
</div>

ForgeAI is a massively parallel, multi-agent AI orchestration platform built on top of **LangGraph** and **FastAPI**. Designed for enterprise scale, ForgeAI autonomously breaks down complex engineering requirements into dynamic, localized execution graphs, compiling software architecture, UML diagrams, codebase structures, and security audits—all in real-time.

### 🌟 Architecture Highlights
- **Compiler-Driven Graph Generation**: Dynamically translates user intent into LangGraph execution graphs.
- **Incremental Regeneration Engine**: Intelligent caching and AST-based change analysis to re-run only what changed.
- **Self-Healing Pipelines**: Automated LLM-driven validation and repair loops (e.g., UML generation constraints).
- **Extensible Provider Factory**: Native drop-in support for multiple foundational models (Gemini, OpenAI, Anthropic).

### 🤝 Supported Providers
- **Google Gemini** (Native multimodal & high-context support)
- **OpenAI** (GPT-4o, o1-preview)
- *Local LLMs via vLLM / Ollama (Planned)*

### 🚀 Quick Links
- [Getting Started](#installation)
- [API Documentation](#api-documentation)
- [Architecture Deep-Dive](#architecture--execution-pipeline)
- [Extending the Graph](#folder-mapping)

---

## 📖 What is ForgeAI?

### Problem Statement
In modern software engineering, translating business requirements into production-ready architecture, code, and documentation requires a village—Solution Architects, Backend Engineers, DevOps, QA, and Security. Current GenAI tools act as standard conversational interfaces, putting the burden of orchestration and state management onto the developer. They lack deterministic workflows, structural memory, and parallelized multi-role execution.

### Motivation
ForgeAI was built to simulate an **entire engineering organization** inside an execution graph. We wanted an orchestration layer that doesn't just "talk back," but rather acts as an autonomous pipeline. When a user requests a feature, ForgeAI automatically provisions a virtual engineering team, assigns specialized roles (agents), establishes a dependency graph, and compiles the output deterministically.

### Goals
1. **Determinism in LLM Workflows**: Ensure that architecture diagrams and schemas are syntactically valid via rigorous validation and repair loops.
2. **Dynamic Graph Orchestration**: Avoid hardcoded state machines. Let the `Planner` agent decide the exact topology of the graph based on the complexity of the request.
3. **Latency Optimization**: Execute non-dependent agents in parallel (e.g., Security Engineer and DevOps Engineer can work simultaneously once the architecture is finalized).
4. **Resiliency**: Enterprise workloads require fault tolerance, API retry policies, and structured failure states.

### Enterprise Use Cases
- **Automated Solutions Architecture**: Instantly generate system topologies, ERD diagrams, and sequence diagrams for RFP responses.
- **Compliance & Security Auditing**: Automatically run new architectural propositions against a localized Security Agent trained on SOC2/SEBI compliance rules.
- **Legacy Codebase Modernization**: Ingest monolithic structures and output microservices boundary definitions with matching PlantUML diagrams.
- **Rapid Prototyping**: Generate boilerplate, CI/CD pipelines, and infrastructure-as-code from a single sentence.

### Example Prompts
> *"Design a highly available Ride Sharing backend handling 10,000 requests per second. Include the sequence diagrams for the driver-matching algorithm and the ERD for the PostgreSQL database."*

> *"Analyze our current E-Commerce checkout flow and redesign it to meet SEBI compliance standards for financial data handling."*

### Expected Outputs
- **Structured JSON**: Detailed architectural components, API schemas, and deployment topologies.
- **Rendered Artifacts**: Scalable Vector Graphics (SVG), PlantUML files, and architecture markdown documents.
- **Execution Traces**: A complete observability dashboard showing the exact path the AI took to arrive at the solution.

---

## 🏛️ Architecture & Execution Pipeline

ForgeAI operates on a highly deterministic, multi-stage compilation and execution pipeline. This section documents the exact flow of data and control from the moment an HTTP request is received to the final payload delivery.

### Complete Execution Flow

```mermaid
flowchart TD
    User([User]) --> FastAPI[FastAPI API]
    FastAPI --> OS[Orchestration Service]
    
    subgraph Orchestration & Planning
        OS --> DWO[Dynamic Workflow Orchestrator]
        DWO --> IA[Intent Analyzer]
        IA --> Planner[Planner Agent]
        Planner --> WC[Workflow Compiler]
    end

    subgraph LangGraph Execution Engine
        WC --> EG[Execution Graph]
        EG --> LGC[LangGraph Compiler]
        LGC --> LGR[LangGraph Runtime]
        
        LGR --> REA[Requirement Extraction Agent]
        REA --> ARA[Architecture Reasoning Agent]
        ARA --> URA[UML Recommendation Agent]
        URA --> UGA[UML Generator Agent]
        
        subgraph Self-Healing Loop
            UGA --> UVA[UML Validator Agent]
            UVA -->|Valid| Ren
            UVA -->|Invalid| URepA[UML Repair Agent]
            URepA --> UVA
        end
        
        Ren[Renderer Agent] --> FA[Feedback Agent]
        FA --> EDA[Execution Dashboard Agent]
    end

    EDA --> Response([Response])
    Response --> User

    classDef core fill:#2d3436,stroke:#74b9ff,stroke-width:2px,color:#fff;
    classDef agent fill:#0984e3,stroke:#74b9ff,stroke-width:2px,color:#fff;
    classDef engine fill:#d63031,stroke:#ff7675,stroke-width:2px,color:#fff;
    classDef user fill:#00b894,stroke:#55efc4,stroke-width:2px,color:#fff;

    class OS,DWO,WC,EG,LGC,LGR core;
    class IA,Planner,REA,ARA,URA,UGA,UVA,URepA,Ren,FA,EDA agent;
    class FastAPI engine;
    class User,Response user;
```

### Component Details

#### 1. FastAPI API
- **Purpose**: Acts as the primary HTTP entry point for external clients.
- **Responsibility**: Handles HTTP protocol semantics, authenticates requests, deserializes JSON payloads using Pydantic schemas, and manages rate limiting.
- **Input**: Raw HTTP POST requests containing user prompts and session metadata.
- **Output**: Validated internal data transfer objects (DTOs).
- **Why it exists**: To abstract HTTP transport details away from the core AI engine.
- **Why separated**: The core engine must remain transport-agnostic (runnable via CLI or gRPC). Coupling HTTP logic to the engine would prevent code reuse.
- **Interaction**: Passes the validated DTO to the `Orchestration Service`.

#### 2. Orchestration Service
- **Purpose**: Serves as the domain service layer that bridges the API and the internal AI workflow.
- **Responsibility**: Manages session state initialization, establishes correlation IDs, and handles high-level error catching and metric tracking for the API.
- **Input**: Validated request DTOs.
- **Output**: Triggers the execution of the dynamic orchestrator and awaits results.
- **Why it exists**: Provides a clean boundary where transactional context (like database session lifecycles) can be managed before heavy AI execution begins.
- **Why separated**: Keeps business logic out of the FastAPI routers, ensuring routers remain thin.
- **Interaction**: Invokes the `Dynamic Workflow Orchestrator`.

#### 3. Dynamic Workflow Orchestrator
- **Purpose**: The master controller for the planning phase.
- **Responsibility**: Determines whether a request requires a brand new graph or an incremental update to an existing session.
- **Input**: User intent and historical session data.
- **Output**: Control flow to the Planning agents.
- **Why it exists**: Prevents the system from blindly executing a fixed DAG. It injects intelligence *before* the LangGraph pipeline is even constructed.
- **Why separated**: It manages the *lifecycle* of the graph, which cannot be managed by the graph itself.
- **Interaction**: Calls the `Intent Analyzer`.

#### 4. Intent Analyzer
- **Purpose**: Determines the semantic intent of the user's prompt.
- **Responsibility**: Classifies the prompt (e.g., "Create new system", "Modify existing system", "Clarify requirements").
- **Input**: Natural language prompt.
- **Output**: A structured Enum representing the intent type.
- **Why it exists**: We need to know *what* we are building before we know *who* needs to build it.
- **Why separated**: NLP classification is a distinct domain from workflow generation. Merging it with the Planner would dilute the prompt focus and reduce LLM fidelity.
- **Interaction**: Passes the intent classification to the `Planner Agent`.

#### 5. Planner Agent
- **Purpose**: Acts as the Lead Architect / Engineering Manager.
- **Responsibility**: Maps the user's intent to a specific set of required downstream agents and defines their execution dependencies.
- **Input**: Intent classification and user prompt.
- **Output**: A JSON array defining the required nodes (agents) and edges (dependencies).
- **Why it exists**: Enables purely dynamic DAGs. If a request doesn't need DevOps, the DevOps agent is never scheduled, saving tokens and time.
- **Why separated**: The Planner decides *what* the graph should look like, but it does not compile it. Separation of concerns between decision-making and graph compilation.
- **Interaction**: Hands the blueprint to the `Workflow Compiler`.

#### 6. Workflow Compiler
- **Purpose**: Translates the AI's declarative JSON blueprint into imperative Python data structures.
- **Responsibility**: Resolves agent dependencies into concrete LangGraph edge definitions.
- **Input**: JSON blueprint from the Planner.
- **Output**: An intermediate `Execution Graph` representation.
- **Why it exists**: AI cannot directly write Python LangGraph code reliably at runtime. It must generate an intermediate representation that is safely compiled.
- **Why separated**: It is purely deterministic Python logic; no LLMs are involved here.
- **Interaction**: Produces the `Execution Graph`.

#### 7. Execution Graph
- **Purpose**: An in-memory intermediate representation (IR) of the workflow.
- **Responsibility**: Holds the nodes, conditional edges, and parallel execution instructions before they are committed to LangGraph.
- **Input**: Data structures from the Workflow Compiler.
- **Output**: IR ready for LangGraph compilation.
- **Why it exists**: Allows us to validate the DAG (detect cycles, missing nodes) before handing it off to the external LangGraph library.
- **Why separated**: Acts as an abstraction layer over LangGraph. If we migrate away from LangGraph in the future, the IR remains unchanged.
- **Interaction**: Read by the `LangGraph Compiler`.

#### 8. LangGraph Compiler
- **Purpose**: Instantiates the actual LangGraph `StateGraph` object.
- **Responsibility**: Binds Python functions (agents) to graph nodes, registers custom state reducers, and compiles the executable graph with a persistent checkpointer.
- **Input**: The Execution Graph IR.
- **Output**: A compiled, runnable `CompiledGraph`.
- **Why it exists**: It isolates the LangGraph-specific API calls (`.add_node()`, `.add_edge()`, `.compile()`) into a single deterministic module.
- **Why separated**: Isolates external library coupling.
- **Interaction**: Returns the graph to be executed by the `LangGraph Runtime`.

#### 9. LangGraph Runtime
- **Purpose**: The execution engine that traverses the compiled DAG.
- **Responsibility**: Manages state passing, parallel thread execution, reducer invocation, and checkpointer persistence.
- **Input**: The compiled graph and the initial `ForgeState`.
- **Output**: The final mutated `ForgeState` after all nodes execute.
- **Why it exists**: It handles the complexities of distributed execution and state merging across parallel agents.
- **Why separated**: It is the engine itself, completely decoupled from the domain logic of the agents it executes.
- **Interaction**: Triggers the `Requirement Extraction Agent`.

#### 10. Requirement Extraction Agent
- **Purpose**: Parses unstructured prompts into structured engineering requirements.
- **Responsibility**: Identifies functional vs. non-functional requirements, constraints, and assumptions.
- **Input**: `ForgeState` containing the raw user prompt.
- **Output**: Mutates `ForgeState` by appending a structured `requirements` list.
- **Why it exists**: Downstream agents (like Architecture) need bullet-pointed, atomic requirements, not conversational text.
- **Why separated**: Splitting extraction from reasoning prevents LLM hallucinations by enforcing a strict single-responsibility prompt.
- **Interaction**: State flows to the `Architecture Reasoning Agent`.

#### 11. Architecture Reasoning Agent
- **Purpose**: Performs critical system design thinking.
- **Responsibility**: Evaluates trade-offs (e.g., SQL vs NoSQL, Monolith vs Microservices) based on extracted requirements and writes Architecture Decision Records (ADRs).
- **Input**: Structured requirements.
- **Output**: Mutated `ForgeState` containing ADRs and high-level component definitions.
- **Why it exists**: Before writing code or drawing diagrams, a system must be conceptually architected.
- **Why separated**: If merged with diagram generation, the LLM often rushes to output syntax without thinking through the distributed systems implications.
- **Interaction**: State flows to the `UML Recommendation Agent`.

#### 12. UML Recommendation Agent
- **Purpose**: Decides *which* diagrams are necessary.
- **Responsibility**: Evaluates the architecture to determine if Sequence, ERD, Component, or Deployment diagrams are needed.
- **Input**: Architecture components and ADRs.
- **Output**: A list of diagram types appended to the state.
- **Why it exists**: Not every prompt requires a database ERD. This saves tokens and generation time.
- **Why separated**: Deciding *what* to draw is semantically different from writing PlantUML syntax.
- **Interaction**: State flows to the `UML Generator Agent`.

#### 13. UML Generator Agent
- **Purpose**: Writes PlantUML syntax.
- **Responsibility**: Translates architecture components into strict PlantUML code blocks for the recommended diagram types.
- **Input**: Recommended diagram types and architectural components.
- **Output**: Raw PlantUML strings in the state.
- **Why it exists**: To create visual, render-able artifacts of the architecture.
- **Why separated**: LLMs struggle with syntax generation; it requires a highly specialized prompt focused purely on PlantUML rules, completely separate from architecture reasoning.
- **Interaction**: State flows to the `UML Validator Agent`.

#### 14. UML Validator Agent
- **Purpose**: Detects syntax errors in generated PlantUML.
- **Responsibility**: Sends the generated PlantUML to a local compiler/server to verify it renders without errors.
- **Input**: Raw PlantUML strings.
- **Output**: A boolean validation flag and an error trace (if any).
- **Why it exists**: LLMs frequently hallucinate PlantUML syntax. We must verify correctness deterministically before rendering.
- **Why separated**: Validation requires external system calls (to a compiler), which is an imperative software operation, not an LLM generation task.
- **Interaction**: If invalid, routes to the `UML Repair Agent`. If valid, routes to the `Renderer Agent`.

#### 15. UML Repair Agent
- **Purpose**: Auto-corrects broken PlantUML syntax.
- **Responsibility**: Ingests the compiler error trace alongside the broken PlantUML and instructs the LLM to fix the specific line number that failed.
- **Input**: Broken PlantUML and compiler error stack trace.
- **Output**: Repaired PlantUML string.
- **Why it exists**: Creates a self-healing pipeline, drastically improving the success rate of complex diagrams.
- **Why separated**: A repair prompt is entirely different from a generation prompt. It focuses strictly on diff-resolution.
- **Interaction**: Loops back to the `UML Validator Agent`.

#### 16. Renderer Agent
- **Purpose**: Converts internal state strings into tangible assets.
- **Responsibility**: Takes valid PlantUML strings and architecture JSON and writes them to the local filesystem as `.svg`, `.png`, and `.md` files.
- **Input**: Finalized, validated state.
- **Output**: Physical files on disk and updated state with file URIs.
- **Why it exists**: The graph must produce consumable artifacts, not just in-memory strings.
- **Why separated**: I/O operations (writing to disk) should be consolidated into a single terminal node to prevent race conditions from parallel agents writing simultaneously.
- **Interaction**: State flows to the `Feedback Agent`.

#### 17. Feedback Agent
- **Purpose**: Prepares the state for future human-in-the-loop interactions.
- **Responsibility**: Analyzes the generated output and highlights ambiguous requirements or trade-offs where human review is recommended.
- **Input**: Rendered artifacts and architecture ADRs.
- **Output**: A list of clarifying questions for the user.
- **Why it exists**: AI cannot make final business decisions. It must proactively request alignment.
- **Why separated**: Feedback generation requires analyzing the *entire* completed output, which can only happen after rendering.
- **Interaction**: State flows to the `Execution Dashboard Agent`.

#### 18. Execution Dashboard Agent
- **Purpose**: Aggregates telemetry for observability.
- **Responsibility**: Summarizes token usage, latency per node, repair loop iterations, and total execution time.
- **Input**: The complete execution trace embedded in the state.
- **Output**: Formatted execution metrics.
- **Why it exists**: Enterprise platforms require auditability and cost tracking.
- **Why separated**: Telemetry aggregation is a distinct reporting concern that should not muddy the core engineering agents.
- **Interaction**: Finalizes the state graph and hands control back to the Orchestration layer, which returns the `Response` to the user.

---

## 🏗️ Why This Architecture?

Enterprise GenAI is not about "sending a prompt to an API." It requires deterministic state management, fault tolerance, and strict separation of concerns. 

- **Why is the project layered?** To isolate side-effects. The API layer handles HTTP, the Orchestration layer handles workflow lifecycles, and the Graph layer handles AI execution. This ensures that changes to the LLM logic do not break the web server, and vice versa.
- **Why doesn't FastAPI directly invoke LangGraph?** Direct invocation couples the web framework to the AI engine. By using an Orchestration Service, we can invoke the same AI engine via a RabbitMQ consumer or a background Celery worker without rewriting the graph logic.
- **Why does the Orchestration Service exist?** It acts as the transaction boundary. It ensures that session metadata, correlation IDs, and memory contexts are fully loaded before the AI ever sees the request.
- **Why does the Dynamic Workflow Orchestrator exist?** Not all requests require the same graph. A simple question ("What is an ERD?") shouldn't trigger the entire UML pipeline. The DWO determines the macro-execution strategy (e.g., skip to Q&A vs. run full pipeline).
- **Why does the Planner exist?** To dynamically map dependencies. Hardcoding a static DAG means wasting tokens on agents that aren't needed. The Planner creates a bespoke virtual engineering team for every unique request.
- **Why does the Workflow Compiler exist?** LLMs output unstructured JSON. The compiler translates this JSON into imperative, strongly-typed Python objects that represent a directed acyclic graph.
- **Why does the Execution Graph exist?** It provides an Intermediate Representation (IR). If we decide to move away from LangGraph to a custom execution engine, the compiler targets the IR, meaning no agent logic needs to change.
- **Why does the LangGraph Compiler exist?** It wraps the LangGraph-specific SDK calls (`add_node`, `add_edge`). Isolating this means we can swap LangGraph versions seamlessly.
- **Why are specialized agents better than one giant prompt?** Context dilution. An LLM cannot effectively act as a Security Engineer, UML Designer, and Code Reviewer simultaneously. Narrow, single-responsibility prompts yield vastly superior fidelity and allow for parallel execution.
- **Why is validation separated from generation?** Generation is a non-deterministic LLM task. Validation is a deterministic software task (compiling syntax). Merging them introduces unreliability.
- **Why is repair separated from validation?** The repair prompt requires the specific compiler stack trace and distinct instructions focused on line-by-line diffing, which would confuse a pure generation prompt.
- **Why is rendering separated from generation?** Generation happens concurrently in parallel branches. Rendering requires disk I/O. Separating it into a terminal node prevents race conditions where multiple agents try to write to the same file simultaneously.
- **Why is feedback separated from execution?** Feedback must be comprehensive. The Feedback Agent must see the *final* rendered architecture to know what questions to ask the user.
- **Why is the dashboard a separate agent?** Telemetry is a cross-cutting concern. A dedicated agent ensures that token counting and latency tracking do not bleed into the business logic of the engineering agents.

---

## 🔄 Request Lifecycle

The lifecycle of a single request through ForgeAI demonstrates how declarative HTTP inputs become rich, interconnected artifacts.

1. **HTTP Ingestion**: `POST /api/v1/orchestrate` receives a JSON payload.
2. **Deserialization**: FastAPI validates the payload via Pydantic and generates a `request_id`.
3. **Session Hydration**: Orchestration Service queries the database for previous `thread_id` history.
4. **Graph Compilation**: The Planner defines the necessary agents, and the Compilers build a bespoke LangGraph `StateGraph`.
5. **Graph Execution**: LangGraph Runtime executes the nodes. Parallel paths are routed according to dependencies, with self-healing loops executing as needed.
6. **Artifact Generation**: The Renderer saves SVGs and Markdown files to disk based on the final state.
7. **HTTP Egress**: The Orchestration Service pulls the finalized `ForgeState`, formats a response DTO, and FastAPI returns HTTP 200 to the client.

---

## 🌊 Data Flow (ForgeState Evolution)

The `ForgeState` is a strictly typed Python dictionary that mutates as it traverses the graph.

```text
[Initial State]
  ├── prompt: "Design a logging service"
  └── history: []

↓ (Intent Analyzer executes)

[Intent Added]
  └── intent: Intent.SYSTEM_DESIGN

↓ (Requirement Extraction executes)

[Requirements Added]
  └── requirements: ["High throughput", "Low latency", "Persistent storage"]

↓ (Architecture Reasoning executes)

[Architecture Added]
  └── adrs: ["Use Kafka for buffering", "Use Elasticsearch for querying"]

↓ (UML Recommendation executes)

[Recommended Diagrams Added]
  └── diagram_types: ["Component", "Sequence"]

↓ (UML Generator executes)

[PlantUML Added]
  └── raw_uml: ["@startuml ... @enduml"]

↓ (UML Validator & Repair executes)

[Validation Results Added]
  ├── is_valid: True
  └── error_trace: None

↓ (Renderer executes)

[Rendered Artifacts Added]
  └── artifact_uris: ["/artifacts/logging_arch.svg"]

↓ (Execution Dashboard executes)

[Execution Metrics Added]
  └── metrics: { tokens: 4500, latency_ms: 12500 }

↓

[Final Response Delivered to User]
```

---

## 📂 Folder Mapping

Every conceptual component maps directly to an isolated boundary within the physical codebase:

| Component | Physical Location | Responsibility |
|-----------|------------------|----------------|
| **FastAPI API** | `api/routers/` | HTTP request routing and Pydantic validation. |
| **Orchestration Service** | `api/services/orchestration_service.py` | Business logic gluing API to Core execution. |
| **Dynamic Workflow Orchestrator** | `core/orchestrator.py` | Decides high-level execution strategy. |
| **Intent Analyzer** | `agents/intent_analyzer/` | Prompt classification agent. |
| **Planner** | `agents/planner/` | Generates node/edge dependencies. |
| **Workflow Compiler** | `core/compilers/workflow_compiler.py` | Converts JSON to Graph IR. |
| **Execution Graph** | `core/models/execution_graph.py` | Pydantic representations of IR nodes/edges. |
| **LangGraph Compiler** | `core/compilers/langgraph_compiler.py` | Binds IR to actual LangGraph SDK calls. |
| **LangGraph Runtime** | `core/engine.py` | Manages `.invoke()` and `.stream()`. |
| **Requirement Extraction Agent** | `agents/requirement_extraction/` | Generates functional requirements. |
| **Architecture Reasoning Agent** | `agents/architecture_reasoning/` | Writes ADRs. |
| **UML Agents (Rec, Gen, Val, Rep)** | `agents/uml_*/` | Self-healing PlantUML pipeline. |
| **Renderer Agent** | `agents/renderer/` | File I/O and SVG generation. |
| **Feedback Agent** | `agents/feedback_agent/` | HitL question generation. |
| **Execution Dashboard Agent** | `agents/execution_dashboard/` | Telemetry formatting. |

---

## 🔄 LangGraph Pipeline Advanced Features

ForgeAI leverages advanced features of `langgraph`:

- **StateGraph**: The global data structure shared across all nodes. Implemented as a Python `TypedDict` with heavily typed fields (Pydantic models).
- **Parallel Execution (`Send` API)**: When the `Planner` identifies agents with no inter-dependencies (e.g., `Security Engineer` and `QA Engineer`), the Workflow Compiler maps them using LangGraph's `Send` API to execute them in parallel, drastically reducing overall latency.
- **Reducers**: Because nodes execute in parallel, state mutations must be deterministic. We use custom `Annotated` reducers in our `StateGraph` (e.g., `operator.add` for lists) to safely merge concurrent outputs.
- **Conditional Edges**: Used heavily in the self-healing loops. (e.g., `UML Validator` -> If valid, go to `Renderer`. If invalid, go to `UML Repair`).

---

## ♻️ Incremental Regeneration

When a user modifies a massive architecture (e.g., *"Change the database from Postgres to MongoDB"*), ForgeAI does **not** re-run the entire graph.

1. **Memory**: The previous `StateGraph` is retrieved via thread_id.
2. **Change Analysis**: The `Change Analysis` agent performs semantic diffing between the old prompt and new prompt.
3. **Reuse**: It invalidates only the downstream dependencies of the change (e.g., `Backend Engineer`, `DevOps Engineer`).
4. **Efficiency**: Agents like `Intent Analyzer` or `Requirement Extraction` are skipped, utilizing cached state, saving LLM tokens and massive amounts of latency.

```mermaid
flowchart TD
    Req([New Follow-up Request]) --> CA[Change Analysis Agent]
    CA --> |Fetch Previous State| Mem[(Session Memory)]
    CA --> |AST/Semantic Diff| Invalidator[Dependency Invalidator]
    Invalidator --> DWO[Dynamic Workflow Orchestrator]
    
    DWO --> NodeA{Is Node State Valid?}
    NodeA --> |Yes| Skip[Skip Agent, Use Cache]
    NodeA --> |No| Exec[Execute Agent]
    
    Skip --> Merge[Merge State]
    Exec --> Merge
    Merge --> Res([Final Response])
```

---

## 🔌 Provider Architecture

ForgeAI uses a strict factory pattern for LLM instantiation, allowing hot-swapping of models without changing agent logic.

```mermaid
classDiagram
    class ProviderFactory {
        +get_provider(config) BaseProvider
    }
    class BaseProvider {
        <<interface>>
        +invoke(messages, tools) Response
        +stream(messages, tools) Iterator
    }
    class GeminiProvider {
        -client: genai
        +invoke()
    }
    class OpenAIProvider {
        -client: OpenAI
        +invoke()
    }
    
    ProviderFactory --> BaseProvider: Instantiates
    BaseProvider <|-- GeminiProvider: Implements
    BaseProvider <|-- OpenAIProvider: Implements
```
Agents request a generic LLM interface. The `ProviderFactory` reads the `.env` configuration and injects the appropriate SDK wrapper.

---

## 💾 Memory Architecture

- **Session Checkpointing**: Backed by PostgreSQL (or SQLite for local dev) using LangGraph's `AsyncPostgresSaver`.
- **Thread IDs**: Every conversation maps to a unique `thread_id`.
- **Conversation History**: Retained persistently, allowing the LLM to contextually understand references like *"Make that previous diagram look like X"*.
- **Artifact Versioning**: Previous SVGs and JSON payloads are snapshot in memory to calculate accurate diffs during Incremental Regeneration.

---

## 🔭 Observability

Enterprise platforms require deep visibility.
- **Structured Logging**: All logs are emitted as JSON with standard keys (`trace_id`, `node_name`, `latency_ms`).
- **Execution Dashboard**: The `Execution Dashboard` agent emits real-time Server-Sent Events (SSE) representing the node transition status.
- **Trace IDs**: Every FastAPI request generates a UUID `request_id`. Every graph execution generates a `workflow_id`.

---

## 📡 API Documentation

<details>
<summary><b><code>POST /api/v1/orchestrate</code></b></summary>
Initiates a new workflow or continues an existing one.

**Request Body:**
```json
{
  "prompt": "Design a highly available URL shortener.",
  "session_id": "uuid-1234",
  "config": {
    "provider": "gemini",
    "model": "gemini-1.5-pro",
    "parallel_execution": true
  }
}
```

**Response (200 OK):**
```json
{
  "status": "completed",
  "workflow_id": "wf-999",
  "artifacts": {
    "architecture_json": "url...",
    "uml_svg": "url..."
  },
  "execution_metrics": {
    "total_latency_ms": 14500,
    "agents_executed": 8,
    "tokens_used": 12400
  }
}
```
</details>

*(Placeholder: Swagger UI Screenshot)*
`![Swagger UI UI Placeholder](https://via.placeholder.com/800x400.png?text=Swagger+UI+Documentation)`

---

## ⚙️ Configuration

Configure ForgeAI via `.env`:

```env
# Core
ENVIRONMENT=production
LOG_LEVEL=INFO

# Providers
GEMINI_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-...
DEFAULT_PROVIDER=gemini

# External Dependencies
PLANTUML_SERVER_URL=http://localhost:8080
GRAPHVIZ_PATH=/usr/bin/dot

# Memory
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/forgeai
```

---

## 💻 Installation

### Prerequisites
- Python 3.11+
- PlantUML Server (Docker recommended)
- PostgreSQL (For persistent memory)

### Step-by-Step

**1. Clone the repository**
```bash
git clone https://github.com/your-org/forge-ai-langgraph.git
cd forge-ai-langgraph
```

**2. Set up Virtual Environment (Mac/Linux)**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
*(Windows: `venv\Scripts\activate`)*

**3. Start Infrastructure (Docker)**
```bash
docker-compose up -d plantuml postgres
```

**4. Configure Environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

---

## 🏃 Running ForgeAI

**Run the FastAPI Server:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Run via CLI:**
```bash
python demo/cli_runner.py --prompt "Design a basic blog API"
```

**Run Tests:**
```bash
pytest tests/ -v --cov=core
```

---

## 🎯 Example Requests

Try these prompts to see the power of ForgeAI:
1. **TODO App**: *"Create a microservices architecture for a Todo app with auth, tasks, and notifications."*
2. **E-Commerce**: *"Design the checkout and inventory reservation system for a high-traffic E-Commerce site."*
3. **SEBI Compliance**: *"Design a stock trading ledger database that strictly adheres to SEBI immutable audit log compliance."*
4. **Hospital Management**: *"Architect a HIPAA-compliant Patient Record Management system."*
5. **Ride Sharing**: *"Map out the geospatial indexing strategy and matchmaking algorithm for a ride-sharing backend."*

---

## 🖼️ Example Outputs

*(Placeholder: Generated Architecture JSON)*
`![JSON Structure](https://via.placeholder.com/600x300.png?text=Generated+Architecture+JSON)`

*(Placeholder: Rendered SVG Architecture)*
`![Architecture SVG](https://via.placeholder.com/800x500.png?text=High-Resolution+Architecture+SVG)`

---

## 🛡️ Production Readiness

ForgeAI is built for Day 2 operations.

- **Fault Tolerance**: Agent nodes include automatic retries with exponential backoff for transient API errors.
- **Scalability**: Graph execution is stateless (relying on PostgreSQL checkpointer). Can be scaled horizontally behind a load balancer.
- **Caching (Future)**: Semantic caching layer via Redis to instantly serve identical architectural requests.
- **Rate Limiting**: Built-in token bucket rate limiting on the FastAPI gateway to prevent provider budget exhaustion.
- **Security**: Prompt injection sanitization and strict API schema validation.

---

## 🧪 Testing

ForgeAI utilizes `pytest` for comprehensive coverage.

- **Unit Tests**: Mocks LLM responses to test graph routing, reducers, and workflow compilation logic.
- **Integration Tests**: Tests the full pipeline against local PlantUML and PostgreSQL instances.
- **End-to-End Tests**: Full HTTP lifecycle tests using `TestClient`.

**To run with coverage:**
```bash
pytest --cov=agents --cov=core --cov=api tests/ --cov-report=html
```

---

## 📸 Screenshots

*(Placeholder: Terminal CLI output)*
`![CLI Output](https://via.placeholder.com/800x400.png?text=Rich+Terminal+Output)`

*(Placeholder: Execution Dashboard UI)*
`![Dashboard UI](https://via.placeholder.com/800x400.png?text=Execution+Dashboard+UI)`

*(Placeholder: Folder Structure Artifacts)*
`![Artifacts Folder](https://via.placeholder.com/300x400.png?text=Generated+Artifacts+in+IDE)`

---

## 🗺️ Roadmap

- [x] Dynamic Graph Compilation
- [x] PlantUML Self-Healing
- [x] Provider Abstraction (Gemini/OpenAI)
- [ ] Semantic Caching Layer
- [ ] Human-in-the-Loop Approval Nodes
- [ ] GitHub App Integration (Direct PR creation)
- [ ] Local LLM Support via Ollama

---

## 🤝 Contributing

We welcome contributions! Please see our `CONTRIBUTING.md` for guidelines on how to add new Agents, configure Providers, and submit Pull Requests. Ensure all new Agents include corresponding unit tests for state mutations.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
