# ForgeAI Demonstration Script

**Target Duration:** 7-10 minutes
**Audience:** Technical stakeholders, Architects, Engineers
**Prerequisites:** ForgeAI is running locally (`python main.py` or FastAPI server).

---

## 1. Introduction (0:00 - 1:00)

**Speaker:**
"Welcome everyone. Today, I want to show you **ForgeAI**—an enterprise-grade Agentic Architecture Orchestration Engine. Designing software systems is usually a manual, slow process. You gather requirements, sketch whiteboards, write architecture docs, and manually draw UML diagrams. ForgeAI automates this entire pipeline using a multi-agent system powered by LangGraph. It takes a single natural language prompt and compiles a fully validated, production-ready architectural blueprint."

## 2. Architecture & The Planner (1:00 - 2:00)

**Speaker:**
"Let's look at how ForgeAI thinks. When we feed it a prompt, it doesn't just pass it to an LLM. It routes it to the **Intent Analyzer** and the **Planner**. The Planner determines exactly which agents need to run and dynamically compiles a LangGraph state machine tailored to the complexity of our request."

*Action: Show `demo_prompt.md` to the audience.*

**Speaker:**
"Here is the prompt we're using today: designing a highly available microservices e-commerce platform with Redis caching and PostgreSQL."

*Action: Run the prompt in the CLI.*

### Checkpoint: Expected Terminal Output
```
▶ Intent Analyzer
✓ Analyzed intent: E-commerce microservices platform.
▶ Planner
✓ Generated dynamic execution graph with 7 nodes.
```

## 3. Execution Graph & Requirement Extraction (2:00 - 3:00)

**Speaker:**
"The graph has been compiled. The first agents to execute are the **Requirement Extraction** and **Backend Engineer** agents. They break down the prompt into strict JSON schemas representing the core entities, databases, and microservices needed."

### Checkpoint: Expected Terminal Output
```
▶ Backend Engineer
✓ Built JSON Architecture (Microservices, Databases, API Gateway).
✓ Extracted Requirements.
```

## 4. Architecture Reasoning & UML Recommendation (3:00 - 4:00)

**Speaker:**
"Now that the foundation is built, ForgeAI reasons about the architecture. The **UML Recommender** analyzes the JSON blueprint and decides which UML diagrams best represent this system. For our e-commerce platform, it recommends a Component Diagram, a Sequence Diagram for checkout, and a Class Diagram."

## 5. Parallel Diagram Generation (4:00 - 5:00)

**Speaker:**
"Here is where the orchestration shines. ForgeAI executes the **UmlGeneratorAgent** for all three diagrams *in parallel* using asyncio. It generates raw PlantUML strings concurrently, drastically reducing overall latency."

### Checkpoint: Expected Terminal Output
```
▶ UML Generator
Generating Component Diagram... (Parallel)
Generating Sequence Diagram... (Parallel)
Generating Class Diagram... (Parallel)
```

## 6. Compiler Validation & The Repair Loop (5:00 - 6:30)

**Speaker:**
"LLMs hallucinate syntax. That's a known problem. ForgeAI solves this with a **Compiler Validation** and **Repair Loop**. Every generated PlantUML string is passed to a local `.jar` compiler. If there is a syntax error, the compiler throws an exception, and the LangGraph dynamically routes the failed diagram to the **UmlRepairAgent**. It fixes the exact line of code and recompiles until it passes."

### Checkpoint: Expected Terminal Output
```
▶ Validation Agent
⚠ Syntax Error detected in Sequence Diagram at line 14.
▶ UML Repair Agent
✓ Applied fix to Sequence Diagram. Recompiling...
✓ Validation Passed.
```

## 7. Rendering & The Execution Dashboard (6:30 - 7:30)

**Speaker:**
"Once all diagrams pass compilation, the **RendererAgent** converts them into SVGs and PNGs. Finally, the **Execution Dashboard** agent aggregates the telemetry."

*Action: Show the Rich CLI Dashboard output.*

**Speaker:**
"Look at this dashboard. We have full observability: Execution Time, LLM Calls made, Repair Attempts triggered, and Latency. It's fully transparent."

### Checkpoint: Expected Terminal Output
```
╭──────────────────────────────────────────────╮
│ ForgeAI Execution Summary                    │
├──────────────────────────────────────────────┤
│ Workflow ID: 4f3b2a...                       │
│ Execution Time: 12.4 sec                     │
│ LLM Calls: 5                                 │
│ Repair Attempts: 1                           │
│ Successful Diagrams: 3                       │
╰──────────────────────────────────────────────╯
```

## 8. Incremental Update & Feedback Pipeline (7:30 - 9:30)

**Speaker:**
"Requirements change. If I want to add an ElasticSearch cluster, I don't want to regenerate everything. I submit an **Incremental Update**. ForgeAI uses a **Change Analysis Agent** to detect the diff. It realizes the Sequence and Class diagrams are unchanged, fetches them from the cache, and only regenerates the Component Diagram."

*Action: Submit incremental update.*

### Checkpoint: Expected Terminal Output
```
▶ Change Analysis
✓ Unchanged: sequence, class (Loaded from cache)
✓ Affected: component (Regenerating)
```

**Speaker:**
"Furthermore, if we notice an architectural anti-pattern, we can use the **Feedback Pipeline** (Active Reinforcement Tuning). We provide a correction, and the ART plugin injects it into the conversation memory. Future workflows will permanently adhere to our architectural standards."

## 9. Conclusion (9:30 - 10:00)

**Speaker:**
"ForgeAI isn't just an LLM wrapper; it's a dynamic, self-healing, enterprise orchestration engine. Thank you."
