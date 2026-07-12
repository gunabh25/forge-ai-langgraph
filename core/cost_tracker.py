"""Cost tracking and token estimation utilities."""
from typing import Dict, Any

# Standard pricing for cost estimation (per 1K tokens)
# Assuming a mixed usage of standard fast models (e.g., GPT-4o-mini / Gemini Flash)
COST_PER_1K_INPUT = 0.00015
COST_PER_1K_OUTPUT = 0.0006

def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a string using a simple heuristic.
    This avoids heavy dependencies like tiktoken unless explicitly needed.
    """
    if not text:
        return 0
    # Average english word is ~4 chars, ~1.3 tokens per word -> len / 4 is a reasonable approximation
    return max(1, len(text) // 4)

def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate the estimated cost based on standard token pricing."""
    return (input_tokens / 1000.0 * COST_PER_1K_INPUT) + (output_tokens / 1000.0 * COST_PER_1K_OUTPUT)

def record_agent_cost(
    metadata: Dict[str, Any],
    agent_name: str,
    input_text: str = "",
    output_text: str = "",
    latency_ms: int = 0,
    cache_hit: bool = False,
    llm_calls: int = 1
) -> None:
    """Records the cost metrics for a given agent in the shared metadata state."""
    if "agent_cost_metrics" not in metadata:
        metadata["agent_cost_metrics"] = {}
        
    metrics = metadata["agent_cost_metrics"].get(agent_name, {
        "calls": 0,
        "cache_hits": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "latency_ms": 0,
        "estimated_cost": 0.0
    })
    
    if cache_hit:
        metrics["cache_hits"] += 1
    else:
        metrics["calls"] += llm_calls
        
        in_tokens = estimate_tokens(input_text)
        out_tokens = estimate_tokens(output_text)
        cost = calculate_cost(in_tokens, out_tokens)
        
        metrics["input_tokens"] += in_tokens
        metrics["output_tokens"] += out_tokens
        metrics["latency_ms"] += latency_ms
        metrics["estimated_cost"] += cost
        
    metadata["agent_cost_metrics"][agent_name] = metrics
