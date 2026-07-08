"""Intent Analyzer Agent implementation."""

import json
from typing import Dict, Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.base import BaseAgent
from core.llm import get_llm
from app.state import ForgeState
from config.logging import get_logger
from core.utils import generate_timestamp

logger = get_logger("agents.intent_analyzer")

INTENTS = [
    "uml_generation",
    "backend_generation",
    "frontend_generation",
    "code_review",
    "security_audit",
    "deployment",
    "testing",
    "architecture_design",
    "requirement_analysis",
    "documentation"
]

class IntentAnalyzerAgent(BaseAgent):
    """Intent Analyzer agent responsible for classifying the engineering task."""
    
    @property
    def name(self) -> str:
        return "Intent Analyzer"
        
    @property
    def description(self) -> str:
        return "Analyzes the user's prompt and classifies the engineering task."
        
    @property
    def capabilities(self) -> List[str]:
        return ["intent_classification", "prompt_analysis"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Intent Analyzer agent step."""
        user_request = state.get("user_request", "").strip()
        logger.info("Intent Analyzer starting execution...", extra={"user_request": user_request})
        
        if not user_request:
            raise ValueError("State validation failed: user_request is empty.")
            
        system_prompt = f"""You are an Intent Analyzer for an AI engineering platform.
Your task is to analyze the user's prompt and classify the engineering task into exactly one of the following intents:
{', '.join(INTENTS)}

Respond ONLY with a valid JSON object containing:
1. "intent": a string from the allowed intents list.
2. "confidence": a float between 0.0 and 1.0.
3. "workflow_specification": an object containing a "required_outputs" array.

For example, if the user asks to generate UML diagrams, the required_outputs should be ["rendered_svg_references"].
If the user asks to update an existing architecture, the required_outputs should be ["rendered_svg_references", "impact_analysis_report"].
If the user asks for architecture design only, it should be ["architecture_json"].

Example:
{{
    "intent": "uml_generation",
    "confidence": 0.97,
    "workflow_specification": {{
        "required_outputs": ["rendered_svg_references"]
    }}
}}

Do NOT include any other text, markdown formatting, or explanation.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User request: {user_request}")
        ]
        
        logger.info("Invoking LLM for Intent Analyzer...")
        llm_response = self.llm.invoke(messages)
        
        # Coerce content to string safely
        response_content = llm_response.content
        if isinstance(response_content, list):
            response_content = "\n".join([str(item) for item in response_content])
        else:
            response_content = str(response_content)
            
        # Clean potential markdown JSON formatting
        clean_content = response_content.replace("```json", "").replace("```", "").strip()
        
        try:
            parsed_result = json.loads(clean_content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {clean_content}")
            parsed_result = {"intent": "unknown", "confidence": 0.0}
            
        logger.info(f"Intent classified: {parsed_result}")
        
        new_message = AIMessage(
            content=json.dumps(parsed_result, indent=2),
            name="intent_analyzer"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "intent_analysis_completed": True,
            "last_updated": generate_timestamp()
        }
        
        state_updates = {
            "intent_classification": parsed_result,
            "messages": [new_message],
            "metadata": updated_metadata
        }
        
        return state_updates


# Automatically register the agent
from core.agent_registry import AgentRegistry
AgentRegistry().register(IntentAnalyzerAgent())
