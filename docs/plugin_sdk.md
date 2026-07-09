# ForgeAI Plugin SDK

The ForgeAI Plugin SDK allows developers to easily create, register, and integrate custom agents (plugins) into the ForgeAI ecosystem. 

By leveraging the SDK, your custom agents will be automatically discovered by the `AgentRegistry` and made available for dynamically planned or statically defined workflows.

## Directory Structure

To ensure your plugin is automatically discovered, place it inside the `plugins/` directory at the root of the project:
```
forge-ai-langgraph/
└── plugins/
    ├── __init__.py
    └── my_custom_plugin/
        ├── __init__.py
        └── agent.py
```

## Creating a Plugin

A valid ForgeAI plugin must:
1. Inherit from `agents.base.BaseAgent`.
2. Implement the `run(self, state: ForgeState) -> Dict[str, Any]` method.
3. Be decorated with `@register_plugin`.

### Using `@register_plugin`

The `@register_plugin` decorator is located in `core.plugins.sdk`. It registers your class with the `AgentRegistry` and allows you to inject metadata dynamically without writing verbose property getters.

```python
from typing import Dict, Any, List
from agents.base import BaseAgent
from core.plugins.sdk import register_plugin
from app.state import ForgeState

@register_plugin(
    name="My Custom Agent",
    description="This agent performs specialized data processing.",
    capabilities=["data_processing"],
    requires=["raw_data"],
    produces=["processed_data"]
)
class MyCustomAgent(BaseAgent):
    
    # You must provide these fallbacks if your type checker complains,
    # but the decorator will override them at runtime.
    @property
    def name(self) -> str: return ""
    @property
    def description(self) -> str: return ""
    @property
    def capabilities(self) -> List[str]: return []
    
    def run(self, state: ForgeState) -> Dict[str, Any]:
        print("My Custom Agent is processing...")
        raw_data = state.get("raw_data", "")
        
        return {
            "processed_data": f"Processed {len(raw_data)} items."
        }
```

## Metadata Options

The `@register_plugin` decorator accepts the following metadata arguments:

*   **`name`** (str): The unique name of the agent. Used by the registry to track the agent.
*   **`description`** (str): A description of what the agent does. Planners use this to decide if this agent is needed.
*   **`capabilities`** (List[str]): A list of capabilities this agent possesses (e.g., `["backend", "api"]`).
*   **`requires`** (List[str]): A list of state keys this agent requires as input before it can run.
*   **`produces`** (List[str]): A list of state keys this agent produces or mutates.

## Validation and Errors

When the ForgeAI application starts up, it auto-discovers all plugins. 
If your plugin fails to load (e.g., syntax error, missing dependencies, or if it doesn't inherit from `BaseAgent`), the server will log an error indicating the failure but will continue to run. You can check the logs for `"Could not auto-load plugin"`.
