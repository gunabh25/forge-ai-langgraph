"""Requirement Analyst Agent implementation."""

from typing import Dict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from core.llm import get_llm
from core.prompts import load_prompt, load_examples
from app.state import ForgeState
from config.logging import get_logger
from core.constants import WorkflowStages, ApprovalStatuses, ArtifactFolders, ArtifactNames
from core.utils import generate_timestamp
from core.artifact_manager import ArtifactManager

logger = get_logger("agents.requirement_analyst")

class RequirementAnalystAgent:
    """Requirement Analyst agent responsible for generating the Requirements Specification."""
    
    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        self.system_prompt = load_prompt("requirement_analyst")
        try:
            self.examples = load_examples("requirement_analyst")
        except FileNotFoundError:
            self.examples = ""
        self.artifact_manager = ArtifactManager()
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm
        
    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Requirement Analyst agent step.
        
        Args:
            state: The current shared ForgeState.
            
        Returns:
            Dictionary of state updates.
        """
        logger.info("Requirement analysis started")
        
        user_request = state.get("user_request", "").strip()
        if not user_request:
            raise ValueError("State validation failed: user_request is empty.")
            
        # Compile prompt content
        prompt_content = self.system_prompt
        if self.examples:
            prompt_content += f"\n\nHere are some examples of the expected requirements specification document:\n{self.examples}"
            
        # Get EM analysis if present
        messages_history = state.get("messages", [])
        em_analysis = ""
        for msg in reversed(messages_history):
            if getattr(msg, "name", "") == "engineering_manager":
                em_analysis = msg.content
                break
                
        # Construct messages
        human_content = f"User Request: {user_request}"
        if em_analysis:
            human_content += f"\n\nEngineering Manager Planning and Guidance:\n{em_analysis}"
            
        messages = [
            SystemMessage(content=prompt_content),
            HumanMessage(content=human_content)
        ]
        
        logger.info("Invoking LLM for Requirement Analyst analysis...")
        llm_response = self.llm.invoke(messages)
        
        # Extract content
        response_content = llm_response.content
        if isinstance(response_content, list):
            response_content = "\n".join([str(item) for item in response_content])
        else:
            response_content = str(response_content)
            
        # Save artifact using ArtifactManager
        saved_path = self.artifact_manager.save_artifact(
            stage=ArtifactFolders.REQUIREMENTS,
            base_name=ArtifactNames.REQUIREMENTS,
            content=response_content,
            ext="md"
        )
        logger.info("Artifact created")
        
        # Build state updates
        new_message = AIMessage(
            content=response_content,
            name="requirement_analyst"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "requirement_analysis_completed": True,
            "last_updated": generate_timestamp()
        }
        
        state_updates = {
            "requirements": response_content,
            "artifacts": {
                ArtifactFolders.REQUIREMENTS: [saved_path]
            },
            "current_stage": WorkflowStages.REQUIREMENT_ANALYSIS,
            "messages": [new_message],
            "metadata": updated_metadata
        }
        
        logger.info("Requirement analysis completed")
        return state_updates
