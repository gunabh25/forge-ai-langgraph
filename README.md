<div align="center">

# ⚙️ ForgeAI

**The Enterprise-Grade Agentic Architecture Orchestration Engine**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-orange.svg)](https://python.langchain.com/docs/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-Production_API-009688.svg)](https://fastapi.tiangolo.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT_4o-green.svg)](https://openai.com)
[![Gemini](https://img.shields.io/badge/Gemini-Pro_1.5-blue.svg)](https://deepmind.google/technologies/gemini/)
[![PlantUML](https://img.shields.io/badge/PlantUML-UML_Generation-yellow.svg)](https://plantuml.com)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF.svg)](https://github.com/features/actions)

ForgeAI is a highly concurrent, multi-agent AI framework designed to automatically generate, validate, and maintain enterprise software architectures. Leveraging LangGraph's dynamic compilation, ForgeAI parses user intent to build full-scale systems, mapping abstract requirements into compilable UML diagrams and deployment-ready blueprints.

[Documentation](#) | [Quick Start](#quick-start) | [API Reference](#api-usage) | [Contributing](#contribution-guide)

</div>

---

## 🌟 Project Overview

Traditional software design is manual, slow, and disconnected from the underlying code. **ForgeAI** bridges the gap between requirements and systems engineering.

By orchestrating specialized AI agents in a strictly validated graph pipeline, ForgeAI translates a natural language prompt (e.g., *"Design a highly available microservices e-commerce platform"*) into concrete software requirements, system architectures, and visually rendered UML diagrams (Component, Sequence, Class, State, etc.).

---

## ✨ Features

- **🧠 Dynamic LangGraph Compilation**: Execution paths are not hardcoded. The Intent Analyzer dynamically graphs the workflow based on the complexity of the request.
- **⚡ Parallel Execution Pipeline**: Independent architecture paths (like sequence diagrams vs. class diagrams) are compiled and executed concurrently via asynchronous orchestration.
- **🔄 Incremental Regeneration**: Say goodbye to regenerating from scratch. ForgeAI performs deep change-impact analysis and strategically regenerates only the affected artifacts.
- **🛠️ UML Repair Pipeline**: Built-in compiler-driven validation. If an AI hallucinates invalid PlantUML syntax, the `ValidationAgent` routes the failure to the `UmlRepairAgent` in a continuous self-healing loop.
- **📝 Conversation Memory**: Context is maintained across sessions. Incremental updates feel like a seamless dialogue with a Staff Engineer.
- **🔄 Active Reinforcement Tuning (ART)**: Built-in human-in-the-loop feedback mechanisms. Correct the system, and it persists the adjustments for future runs.
- **📊 Execution Dashboard**: A terminal-based Rich UI and a comprehensive `/metrics` API for complete observability of latencies, token counts, and execution state.

---

## 🏗️ Architecture

ForgeAI operates as a state-driven DAG (Directed Acyclic Graph), compiled dynamically at runtime. 

![High Level Architecture](docs/architecture/01_high_level_architecture.mmd) *(Preview of Architecture, see `docs/architecture/` for all Mermaid/PlantUML source)*

### Execution Pipeline

1. **API Layer**: Receives the prompt and allocates a unique Execution ID.
2. **Intent Analysis**: Determines which architectural components are required.
3. **Graph Compilation**: The Orchestrator compiles a custom LangGraph mapping out the execution.
4. **Backend Engineering**: Core system constraints and components are generated.
5. **Parallel UML Generation**: Dedicated agents draft PlantUML code.
6. **Compiler Validation**: PlantUML syntax is strictly validated. Errors trigger the self-healing loop.
7. **Rendering**: Validated code is converted into localized SVGs and PNGs.
8. **Dashboarding**: Execution metrics are finalized and returned.

---

## 🤖 Supported Agents

| Agent Name | Role |
| :--- | :--- |
| **IntentAnalyzerAgent** | Parses the prompt, identifies complexity, and determines the LangGraph execution plan. |
| **BackendEngineerAgent** | Acts as the Principal Engineer, defining microservices, database schemas, and protocols. |
| **UmlGeneratorAgent** | Translates the JSON architecture into raw PlantUML strings. |
| **ValidationAgent** | The QA Compiler. Tests syntax correctness against a local PlantUML `.jar`. |
| **UmlRepairAgent** | The debugger. Iterates over validation errors to resolve syntax hallucinations. |
| **RendererAgent** | Executes the final `.jar` to output clean SVG/PNG binaries. |
| **ChangeAnalysisAgent** | Analyzes diffs during updates to enable Incremental Regeneration. |
| **ExecutionDashboardAgent** | Aggregates logs, emits telemetry, and visualizes the timeline. |

---

## 📐 Supported UML Diagrams

ForgeAI currently supports the automatic generation of:
- **Component Diagrams** (Microservices, Databases, External APIs)
- **Sequence Diagrams** (Auth flows, API requests, Data pipelines)
- **Class Diagrams** (Entity relationships, Domain Driven Design)
- **State Diagrams** (Lifecycle states, Order processing)
- **Use Case Diagrams** (Actor interactions)
- **Deployment Diagrams** (Cloud infrastructure, VPCs, Kubernetes)

---

## 🔌 Provider Support

ForgeAI uses an abstract `Factory` pattern to support multiple foundational models out of the box:
- **OpenAI**: `gpt-4o`, `gpt-4-turbo`
- **Google DeepMind**: `gemini-1.5-pro`, `gemini-1.5-flash`
- **Anthropic**: `claude-3-5-sonnet`
- *(Extensible to any LangChain-compliant provider)*

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- Java (Required for local PlantUML rendering)
- Graphviz (Required for PlantUML layouts)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/forgeai.git
   cd forgeai
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Add your OPENAI_API_KEY or GOOGLE_API_KEY
   ```

---

## ⚡ Quick Start

### Run the API Server
Start the production-grade FastAPI server:
```bash
uvicorn api.main:app --reload
```
Navigate to `http://localhost:8000/docs` to view the interactive Swagger UI.

### CLI Execution
You can also run ForgeAI directly from the terminal with the rich observability dashboard:
```bash
python main.py
```

---

## 🌐 API Usage

ForgeAI exposes a highly typed REST API.

**Generate a new architecture:**
```bash
curl -X POST "http://localhost:8000/api/v1/generate" \
     -H "Content-Type: application/json" \
     -d '{
           "prompt": "Design a highly available microservices e-commerce platform.",
           "diagram_types": ["component", "sequence"]
         }'
```

**Get System Metrics:**
```bash
curl -s http://localhost:8000/api/v1/metrics
```

---

## 📸 Screenshots

*(Replace with actual screenshots of the CLI dashboard and SVG outputs)*

| CLI Dashboard | Generated Component Diagram |
|:---:|:---:|
| ![CLI Dashboard Placeholder](docs/assets/cli_dashboard_placeholder.png) | ![Diagram Placeholder](docs/assets/diagram_placeholder.png) |

---

## 📂 Folder Structure

```text
forgeai/
├── agents/             # Modular LangGraph Agent definitions
├── api/                # FastAPI routers, schemas, and dependencies
├── app/                # Dynamic Graph orchestration logic
├── artifacts/          # Output directory for rendered SVGs/PNGs
├── config/             # System and Logger configurations
├── core/               # Providers, Compilers, Dynamic Executors, Telemetry
├── docs/               # Architecture diagrams and documentation
├── plantuml/           # Local PlantUML binaries
└── main.py             # CLI Entrypoint
```

---

## 🧠 Advanced Capabilities

### Incremental Regeneration
When calling the `/update` endpoint, ForgeAI hashes the previous state, isolates the specific services affected by the prompt, and skips execution for unaffected nodes, drastically reducing LLM token costs and latency.

### Compiler-driven Validation
LLMs are prone to syntax errors. Instead of failing silently, ForgeAI compiles the generated PlantUML string in memory. If a syntax error is caught by the compiler, the `UmlRepairAgent` is injected dynamically into the graph to fix the exact line of code before proceeding.

### Parallel Execution
When a user requests multiple diagrams (e.g., Component, Sequence, and Class), the dynamic orchestrator forks the DAG into parallel execution nodes using Python `asyncio`, rendering all diagrams simultaneously.

---

## 🗺️ Roadmap

- [x] LangGraph Dynamic Orchestration
- [x] Multi-Diagram Generation
- [x] Compiler Self-Healing Loop
- [x] Parallel Node Execution
- [x] FastAPI REST Layer
- [ ] Terraform Code Generation
- [ ] AWS/GCP Native Integration
- [ ] Interactive Web UI Studio

---

## 📄 License

Distributed under the Apache 2.0 License. See `LICENSE` for more information.

---
<div align="center">
  <b>Built with ❤️ by Gunabh Sharan.</b>
</div>
