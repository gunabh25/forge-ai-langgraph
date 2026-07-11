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
- [Architecture Deep-Dive](#high-level-architecture)
- [Extending the Graph](#agents)

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

## 🏛️ High Level Architecture

ForgeAI adopts a **Compiler-Driven Graph Architecture**. Instead of statically defining a pipeline, ForgeAI receives a request, analyzes it, and *compiles* a custom LangGraph state machine tailored specifically to the problem.

```mermaid
flowchart TD
    User([User Request]) --> FastAPI[FastAPI Gateway]
    FastAPI --> OS[Orchestration Service]
    
    subgraph Orchestration Layer
        OS --> DWO[Dynamic Workflow Orchestrator]
        DWO --> IA[Intent Analyzer]
        IA --> Planner[Planner]
        Planner --> WC[Workflow Compiler]
    end

    subgraph LangGraph Execution Engine
        WC --> EG[Execution Graph Definition]
        EG --> LGC[LangGraph Compiler]
        LGC --> LGR[LangGraph Runtime]
        
        LGR --> ParallelAgents{Parallel Agents}
        ParallelAgents --> |State Update| Renderer[Renderer / Aggregator]
    end

    Renderer --> Dashboard[Execution Dashboard]
    Dashboard --> Response([Final Response / Artifacts])

    classDef core fill:#2d3436,stroke:#74b9ff,stroke-width:2px,color:#fff;
    classDef agent fill:#0984e3,stroke:#74b9ff,stroke-width:2px,color:#fff;
    classDef engine fill:#d63031,stroke:#ff7675,stroke-width:2px,color:#fff;

    class OS,DWO,WC,LGC,LGR core;
    class IA,Planner,ParallelAgents,Renderer agent;
    class FastAPI,Dashboard engine;
```

---

## ⚙️ End-to-End Execution Flow

Every request traversing ForgeAI follows a rigorous, multi-stage lifecycle.

### 1. Ingestion (FastAPI & Orchestration Service)
- **Purpose**: Exposes the system to the outside world, validates payload structures, and assigns unique correlation IDs.
- **Input**: REST HTTP POST payload containing user prompt, session ID, and configuration parameters.
- **Output**: Validated Pydantic models routed to the Orchestration Service.
- **Interaction**: Hands off the sanitized request to the `Dynamic Workflow Orchestrator`.

### 2. Analysis & Planning (Intent Analyzer & Planner)
- **Purpose**: Understands *what* the user wants and *who* is needed to build it.
- **Input**: Natural language prompt.
- **Output**: A JSON array of required agents and their dependency constraints.
- **Interaction**: The `Planner` does not execute the agents. It acts as an architect, passing the blueprint to the `Workflow Compiler`.

### 3. Compilation (Workflow Compiler & LangGraph Compiler)
- **Purpose**: Translates the Planner's JSON output into a runnable `StateGraph`.
- **Input**: Agent dependencies and required deliverables.
- **Output**: A compiled LangGraph `CompiledGraph` object.
- **Interaction**: Uses `add_node` and `add_edge` dynamically. Implements LangGraph's `Send` API to map parallel execution branches based on dependency resolution.

### 4. Execution (LangGraph Runtime & Parallel Agents)
- **Purpose**: The actual heavy lifting. Models are invoked, code is written, and diagrams are generated.
- **Input**: Global shared State (containing history, requirements, and intermediate outputs).
- **Output**: Mutated state with generated artifacts.
- **Interaction**: Agents run in parallel. A reducer merges their outputs into the global state securely to prevent race conditions.

### 5. Finalization (Renderer & Dashboard)
- **Purpose**: Aggregates the unstructured/structured state data into beautiful, human-readable formats (Markdown, SVG).
- **Input**: Completed graph state.
- **Output**: Final artifacts written to disk and API response payload.
- **Interaction**: Streams execution telemetry to the observability dashboard while returning the HTTP response to the user.

---

## 📁 Complete Folder Structure

ForgeAI strictly adheres to Domain-Driven Design (DDD) principles. The architecture ensures separation of concerns, keeping the graph compilation logic entirely isolated from the agent definitions and API transport layer.

<details>
<summary><b>Click to expand full directory tree</b></summary>

```text
forge-ai-langgraph/
├── agents/                       # Independent Agent definitions
│   ├── ai_software_engineer/     # Code generation agent
│   ├── architecture_reasoning/   # System design evaluation
│   ├── backend_engineer/         # API and logic design
│   ├── change_analysis/          # AST/Diff analysis for incremental updates
│   ├── code_reviewer/            # Static analysis and best practices
│   ├── devops_engineer/          # Infrastructure and CI/CD
│   ├── engineering_manager/      # Task breakdown and timeline estimation
│   ├── execution_dashboard/      # Telemetry aggregation agent
│   ├── feedback_agent/           # User feedback incorporation
│   ├── intent_analyzer/          # Request classification
│   ├── planner/                  # Graph topology generator
│   ├── qa_engineer/              # Test case generation
│   ├── renderer/                 # Final artifact compiler
│   ├── requirement_analyst/      # Requirement extraction & refinement
│   ├── requirement_extraction/   # Initial data parsing
│   ├── security_engineer/        # Threat modeling and compliance
│   ├── solution_architect/       # High level system definitions
│   ├── uml_generator/            # PlantUML syntax generator
│   ├── uml_recommendation/       # Diagram type selection
│   ├── uml_repair/               # Syntax error auto-correction loop
│   └── uml_validator/            # Syntax validation against PlantUML server
├── api/                          # HTTP Transport Layer (FastAPI)
│   ├── dependencies/             # Dependency Injection (Auth, DB, Logging)
│   ├── routers/                  # API Endpoints
│   ├── schemas/                  # Pydantic validation models
│   └── services/                 # Business logic gluing API to Core
├── app/                          # Main application factory and entry points
├── artifacts/                    # Generated outputs (ignored in git)
│   ├── architecture/             
│   ├── backend/                  
│   ├── diagrams/                 
│   ├── implementation/           
│   ├── reasoning/                
│   ├── reports/                  
│   ├── requirements/             
│   ├── timeline/                 
│   ├── training/                 
│   └── uml/                      
├── config/                       # Environment configuration (Pydantic BaseSettings)
├── core/                         # Core execution engine and utilities
│   ├── compilers/                # Dynamic Graph compilers
│   ├── feedback/                 # Human-in-the-loop logic
│   ├── models/                   # Global state definitions (LangGraph TypedDict)
│   ├── plugins/                  # Plugin registry
│   └── providers/                # LLM Provider Factory (Gemini, OpenAI)
├── demo/                         # UI/CLI demos
├── docs/                         # Extended documentation
├── examples/                     # Example payloads and outputs
├── logs/                         # Structured JSON application logs
├── mcp/                          # Model Context Protocol servers/definitions
├── memory/                       # Checkpointing and session storage
├── models/                       # Domain models (SQLAlchemy/Pydantic)
├── plugins/                      # Extendable user-defined agents/tools
│   └── example_plugin/           
├── schemas/                      # Global system schemas
└── tests/                        # Pytest suite
    ├── integration/              # Database & Graph integration tests
    └── smoke/                    # Health checks
```
</details>

### Directory Responsibilities
- **`agents/`**: Contains the logic, system prompts, and tool access for every individual AI actor. Every agent is self-contained. It interacts with the `core/` to read/write state.
- **`api/`**: The FastAPI application layer. It interacts *only* with `services/` and never directly invokes an LLM.
- **`core/`**: The brain of ForgeAI. Contains the `LangGraph` compilation logic, global state reducers, and provider abstraction layer. It imports from `agents/` to build the graph.
- **`memory/`**: Manages state persistence across conversational turns, enabling incremental regeneration. Interacts heavily with `core/compilers`.
- **`artifacts/`**: The physical output directory where the `Renderer` saves SVGs, JSONs, and Markdown.

---

## 🤖 Agents

ForgeAI operates via a highly specialized swarm of AI agents. Each agent receives a subset of the global state, processes it using specific tools and system prompts, and returns a state mutation.

| Agent | Responsibility | Input | Output | Dependencies |
|-------|----------------|-------|--------|--------------|
| **Intent Analyzer** | Determines if request is new, a modification, or a query. | User Prompt | Intent Enum, Sub-tasks | None |
| **Planner** | Generates the dynamic DAG of required agents. | Intent, Prompt | JSON List of Agents & Edges | Intent Analyzer |
| **Requirement Extraction** | Parses prompt into structured functional requirements. | Prompt | Functional/Non-Functional Reqs | Planner |
| **Requirement Analyst** | Refines raw requirements into technical specifications. | Extracted Reqs | Tech Specs, Edge Cases | Requirement Extraction |
| **Architecture Reasoning** | Evaluates tradeoffs between different system designs. | Tech Specs | Architecture Decision Record | Requirement Analyst |
| **Solution Architect** | Designs the high-level system components and microservices. | Architecture Decisions | Component JSON, ERDs | Architecture Reasoning |
| **UML Recommendation** | Decides which UML diagrams are needed for the architecture. | Component JSON | List of diagram types | Solution Architect |
| **UML Generator** | Writes Raw PlantUML syntax. | Components, Diagram Types | PlantUML Syntax Strings | UML Recommendation |
| **UML Validator** | Compiles PlantUML to detect syntax errors. | PlantUML Syntax | Boolean Valid, Error Trace | UML Generator |
| **UML Repair** | Auto-corrects invalid PlantUML syntax. | Syntax, Error Trace | Fixed PlantUML Syntax | UML Validator |
| **Backend Engineer** | Designs API contracts (OpenAPI) and database schemas. | Components | OpenAPI JSON, SQL DDL | Solution Architect |
| **Security Engineer** | Threat modeling and compliance verification (e.g., OWASP). | Components, APIs | Security Audit Report | Backend Engineer |
| **DevOps Engineer** | Defines infrastructure (Terraform/Docker) and CI/CD. | Components, APIs | IaC Definitions | Backend Engineer |
| **QA Engineer** | Generates test plans and integration test scenarios. | Tech Specs, APIs | Test Matrix | Backend Engineer |
| **Engineering Manager** | Estimates story points, timeline, and resource allocation. | Tech Specs, Architecture | Project Timeline (Gantt) | Solution Architect |
| **AI Software Engineer** | Generates actual boilerplate code for the designed backend. | APIs, DDL | Source Code files | Backend Engineer |
| **Code Reviewer** | Static analysis of AI-generated code. | Source Code files | Code Review Comments | AI Software Engineer |
| **Change Analysis** | Detects diffs in prompts for incremental runs. | Previous State, New Prompt | AST Diff, Invalidation List | Memory |
| **Renderer** | Compiles all outputs into Markdown/SVG artifacts. | Global State | Files written to disk | All Agents |
| **Feedback** | Integrates Human-in-the-Loop review feedback. | State, User Feedback | Updated Requirements | Renderer |
| **Execution Dashboard** | Emits WebSocket/Log telemetry of execution. | Global State | Telemetry Events | All Agents |

---

## 🧠 Orchestration Layer

The Orchestration Layer is the bridge between the API transport and the LangGraph Engine.

### Why is this layer separated?
If FastAPI called LangGraph directly, the API would be tightly coupled to the state machine. By abstracting this into an `Orchestration Service` and a `Dynamic Workflow Orchestrator`, we achieve:
1. **Transport Agnosticism**: The exact same orchestrator can be invoked via CLI, Message Queue (RabbitMQ), or gRPC, not just FastAPI.
2. **Dynamic Compilation**: Standard LangGraph implementations define a static `StateGraph`. The `Workflow Compiler` builds the `StateGraph` *at runtime* based on the Planner's output.

- **Workflow Compiler**: Translates abstract dependencies (e.g., `Backend Engineer` depends on `Solution Architect`) into strict LangGraph `Edges` and `Conditional Edges`.
- **Execution Graph**: An intermediate representation (IR) of the workflow before it is handed to LangGraph.
- **LangGraph Compiler**: Takes the IR and invokes `.compile()` with the designated `checkpointer` (Memory) for persistence.

---

## 🔄 LangGraph Pipeline

ForgeAI leverages advanced features of `langgraph`:

- **StateGraph**: The global data structure shared across all nodes. Implemented as a Python `TypedDict` with heavily typed fields (Pydantic models).
- **Parallel Execution (`Send` API)**: When the `Planner` identifies agents with no inter-dependencies (e.g., `Security Engineer` and `QA Engineer`), the Workflow Compiler maps them using LangGraph's `Send` API to execute them in parallel, drastically reducing overall latency.
- **Reducers**: Because nodes execute in parallel, state mutations must be deterministic. We use custom `Annotated` reducers in our `StateGraph` (e.g., `operator.add` for lists) to safely merge concurrent outputs.
- **Conditional Edges**: Used heavily in the self-healing loops. (e.g., `UML Validator` -> If valid, go to `Renderer`. If invalid, go to `UML Repair`).

---

## 🎨 UML Pipeline

Generating valid PlantUML from LLMs is notoriously flaky. ForgeAI implements a deterministic **Self-Healing Compiler Loop** within the graph.

```mermaid
sequenceDiagram
    participant Architect as Solution Architect
    participant Rec as UML Recommendation
    participant Gen as UML Generator
    participant Val as UML Validator
    participant Rep as UML Repair
    participant Ren as Renderer

    Architect->>Rec: Provide System Components
    Rec->>Gen: Request Diagram Types (e.g., Sequence, Component)
    Gen->>Val: Generate Raw PlantUML Syntax
    
    loop Validation & Repair Loop (Max Retries: 3)
        Val->>Val: Local PlantUML Compilation Check
        alt Syntax is Valid
            Val->>Ren: Send Valid Syntax
        else Syntax Error Detected
            Val->>Rep: Send Syntax + Compiler Error Trace
            Rep->>Val: Return Repaired Syntax
        end
    end
    
    Ren->>Ren: Render SVG / PNG
```

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

## 🧠 Design Decisions

- **Why LangGraph?** Over LangChain/AutoGen, LangGraph provides first-class support for cyclical graphs, state reduction, and fine-grained checkpointing, essential for self-healing loops.
- **Why PlantUML?** It is text-based and highly structured, making it much easier for LLMs to generate correctly compared to direct SVG or XML generation.
- **Why Multiple Agents?** A single LLM prompt degrades in quality as output complexity increases. Narrowing context to specific persona roles (e.g., Security Engineer) yields dramatically higher fidelity.
- **Why Compiler-Driven Validation?** We don't trust LLMs to write correct code on the first try. By running PlantUML syntax through a local compiler, we get deterministic error traces to feed back into the repair loop.
- **Why Provider Abstraction?** To prevent vendor lock-in and allow fallback logic (e.g., if OpenAI rate limits, failover to Gemini).

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
