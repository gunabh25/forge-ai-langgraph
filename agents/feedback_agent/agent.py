"""Feedback Agent implementation."""

import json
from typing import Dict, Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from agents.base import BaseAgent
from core.agent_registry import AgentRegistry
from app.state import ForgeState
from config.logging import get_logger
from core.utils import generate_timestamp
from core.feedback.manager import FeedbackManager
from core.feedback.art_plugin import ARTPluginInterface
from core.feedback.models import UserFeedbackEntry

logger = get_logger("agents.feedback")

class StubARTPlugin(ARTPluginInterface):
    """Stub implementation of ARTPluginInterface for forwarding feedback."""
    def process_feedback(self, entry: UserFeedbackEntry) -> None:
        logger.info(f"StubARTPlugin processing feedback {entry.feedback_id}")
        
    def generate_reward_score(self, entry: UserFeedbackEntry) -> float:
        return 1.0
        
    def get_plugin_status(self) -> Dict[str, Any]:
        return {"status": "mock_art_plugin", "ready": True}

class FeedbackAgent(BaseAgent):
    """Agent responsible for capturing and forwarding feedback to the ART Plugin."""
    
    @property
    def name(self) -> str:
        return "Feedback Agent"
        
    @property
    def description(self) -> str:
        return "Captures structured user feedback and forwards it to the ART Plugin Interface."
        
    @property
    def capabilities(self) -> List[str]:
        return ["feedback_collection", "art_integration"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        self.feedback_manager = FeedbackManager(art_plugin=StubARTPlugin())

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            # Fallback to a stub model if needed, but not heavily reliant on LLM
            from core.llm import get_llm
            self._llm = get_llm()
        return self._llm
        
    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Feedback Agent."""
        logger.info("Feedback Agent starting execution.")
        
        user_request = state.get("user_request", "")
        architecture = state.get("architecture_json") or state.get("architecture", "")
        plantuml_diagrams = state.get("plantuml_diagrams", {})
        user_feedback = state.get("user_feedback", "")
        
        if not user_feedback:
            logger.info("No user feedback provided in state. Skipping feedback storage.")
            return {}
            
        # Serialize structures for storage compatibility
        arch_str = json.dumps(architecture, indent=2) if isinstance(architecture, dict) else str(architecture)
        uml_str = json.dumps(plantuml_diagrams, indent=2)
        
        # Submit feedback, which automatically forwards to the configured ART plugin
        entry = self.feedback_manager.submit_feedback(
            user_id="system_user",
            project_id="forgeai_project",
            prompt=user_request,
            generated_uml=uml_str,
            user_feedback=user_feedback,
            metadata={"architecture": arch_str}
        )
        
        new_message = AIMessage(
            content=f"Feedback collected and forwarded to ART Plugin with ID {entry.feedback_id}",
            name="feedback_agent"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "feedback_forwarded": True,
            "feedback_id": entry.feedback_id,
            "last_updated": generate_timestamp()
        }
        
        return {
            "messages": [new_message],
            "metadata": updated_metadata,
            "current_stage": "feedback_agent"
        }

# Automatically register the agent
AgentRegistry().register(FeedbackAgent())
