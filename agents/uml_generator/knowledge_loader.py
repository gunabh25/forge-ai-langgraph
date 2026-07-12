"""Dynamic Knowledge Loader for PlantUML Grammar Examples."""

import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("agents.uml_generator.knowledge_loader")

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
_CACHE: Dict[str, List[str]] = {}

def get_grammar_examples(diagram_type: str, max_examples: int = 3, max_chars: int = 700) -> str:
    """Load grammar examples for a specific diagram type, caching them in memory.
    
    Reads from agents/uml_generator/knowledge/{diagram_type}_examples.md
    Selects up to `max_examples`. Truncates if exceeding `max_chars` by dropping examples.
    """
    file_path = _KNOWLEDGE_DIR / f"{diagram_type}_examples.md"
    
    if diagram_type not in _CACHE:
        if not file_path.exists():
            return ""
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info("Grammar examples loaded from disk | file=%s", file_path.name)
            
            # Split by markdown headers
            raw_examples = content.split("## ")
            examples = []
            for ex in raw_examples[1:]: # skip the main header
                examples.append("## " + ex.strip())
            _CACHE[diagram_type] = examples
        except Exception as e:
            logger.error("Failed to load grammar examples | file=%s | error=%s", file_path.name, str(e))
            _CACHE[diagram_type] = []
            
    all_examples = _CACHE.get(diagram_type, [])
    if not all_examples:
        return ""
        
    selected_examples = all_examples[:max_examples]
    
    # Truncate intelligently by dropping examples if they exceed max_chars
    while selected_examples:
        combined = "\n\n".join(selected_examples)
        if len(combined) <= max_chars:
            break
        selected_examples.pop()
        
    final_output = "\n\n".join(selected_examples)
    
    logger.info(
        "Grammar examples injected | diagram_type=%s | count=%d | chars=%d | estimated_tokens=%d",
        diagram_type,
        len(selected_examples),
        len(final_output),
        len(final_output) // 4
    )
    
    return final_output
