# ForgeAI Architecture Diagrams

## 01 High Level Architecture

```mermaid
graph TD
    API[FastAPI REST Layer] --> ORCH[Orchestration Service]
    ORCH --> MEM[Memory Context]
    ORCH --> REG[Agent Registry]
    ORCH --> EXEC[Dynamic Executor]
    EXEC --> STORE[(Execution Store)]
    EXEC --> MON[Telemetry & Monitoring]
```

## 02 Agent Interaction

```mermaid
sequenceDiagram
    actor User
    participant Orch as API / Orchestrator
    participant Intent as IntentAnalyzerAgent
    participant Backend as BackendEngineerAgent
    participant UML as UmlGeneratorAgent
    participant Validator as ValidationAgent
    participant Renderer as RendererAgent

    User->>Orch: Prompt
    Orch->>Intent: Analyze Intent & Plan Graph
    Intent->>Backend: Build Architecture (Parallel)
    Intent->>Backend: Extract Requirements (Parallel)
    Backend->>UML: Build PlantUML
    UML->>Validator: Validate Syntax
    Validator->>Renderer: Render SVG/PNG
    Renderer->>Orch: Return Artifacts
    Orch->>User: Complete
```

## 03 Dynamic Langgraph Compilation

```mermaid
graph LR
    Intent[IntentAnalyzer] -->|JSON Execution Plan| Compiler[WorkflowCompiler]
    Compiler -->|Add Nodes| Graph[LangGraph StateGraph]
    Compiler -->|Add Conditional Edges| Graph
    Compiler -->|Compile| Graph
```

## 04 Parallel Execution Pipeline

```mermaid
stateDiagram-v2
    state "Parallel Execution" as parallel {
        [*] --> RendererComponent
        [*] --> RendererSequence
        [*] --> RendererClass
    }
```

## 05 Incremental Regeneration

```mermaid
graph TD
    Req[Update Request] --> Change[Change Analysis Agent]
    Change -->|Affected| Exec[Execution Pipeline]
    Change -->|Unchanged| Cache[Cache Manager]
    Cache -->|Inject Cached SVGs| Exec
    Exec --> Out[New Artifacts]
```

## 06 Uml Repair Pipeline

```mermaid
flowchart TD
    Start --> Gen[Generate PlantUML]
    Gen --> Val[Validate Syntax]
    Val --> Cond{Syntax Error?}
    Cond -->|Yes| Repair[Send to Repair Agent]
    Repair --> Fix[Fix Syntax]
    Fix --> Val
    Cond -->|No| Render[Render Artifact]
    Render --> Stop
```

## 07 Provider Abstraction

```mermaid
classDiagram
    class BaseChatModel
    class OpenAIProvider
    class AnthropicProvider
    class GoogleProvider

    BaseChatModel <|-- OpenAIProvider
    BaseChatModel <|-- AnthropicProvider
    BaseChatModel <|-- GoogleProvider
```

## 08 Conversation Memory

```mermaid
graph TD
    Req[User Request] --> Manager[Memory Manager]
    Manager -->|Load History| Session[(Memory Store / Session)]
    Session --> Context[Context Injection]
    Context --> LLM
```

## 09 Feedback Art Pipeline

```mermaid
graph LR
    Human --> API[Feedback API]
    API --> Manager[Feedback Manager]
    Manager --> ART[ART Plugin]
    ART --> Store[(Memory Store)]
```

## 10 Execution Dashboard

```mermaid
graph TD
    Observer[ExecutionObserver] -->|Publish Event| PubSub[WorkflowEventManager]
    PubSub --> Events[Telemetry Events]
    Events --> CLI[CLI Dashboard]
```

