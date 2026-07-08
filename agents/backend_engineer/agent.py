"""Backend Engineer Agent implementation."""

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

logger = get_logger("agents.backend_engineer")

class BackendEngineerAgent:
    """Backend Engineer agent responsible for generating the Backend Blueprint."""
    
    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        self.system_prompt = load_prompt("backend_engineer")
        try:
            self.examples = load_examples("backend_engineer")
        except FileNotFoundError:
            self.examples = ""
        self.artifact_manager = ArtifactManager()
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm
        
    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Backend Engineer agent step.
        
        Args:
            state: The current shared ForgeState.
            
        Returns:
            Dictionary of state updates.
        """
        logger.info("Backend generation started")
        
        # pyrefly: ignore [missing-attribute]
        requirements = state.get("requirements", "").strip()
        # pyrefly: ignore [missing-attribute]
        architecture = state.get("architecture", "").strip()
        if not requirements or not architecture:
            raise ValueError("State validation failed: requirements or architecture are missing.")
            
        # Compile prompt content
        prompt_content = self.system_prompt
        if self.examples:
            prompt_content += f"\n\nHere are some examples of the expected backend blueprint document:\n{self.examples}"
            
        # Get EM analysis if present
        messages_history = state.get("messages", [])
        em_analysis = ""
        for msg in reversed(messages_history):
            if getattr(msg, "name", "") == "engineering_manager":
                em_analysis = msg.content
                break
                
        # Construct messages
        human_content = f"Requirements Specification:\n{requirements}\n\nArchitecture Specification:\n{architecture}"
        if em_analysis:
            human_content += f"\n\nEngineering Manager Initial Context & Guidance:\n{em_analysis}"
            
        messages = [
            SystemMessage(content=prompt_content),
            HumanMessage(content=human_content)
        ]
        
        logger.info("Invoking LLM for Backend Engineer design...")
        llm_response = self.llm.invoke(messages)
        
        # Extract content
        response_content = llm_response.content
        if isinstance(response_content, list):
            response_content = "\n".join([str(item) for item in response_content])
        else:
            # pyrefly: ignore [unnecessary-type-conversion]
            response_content = str(response_content)
            
        # Save artifact using ArtifactManager
        saved_path = self.artifact_manager.save_artifact(
            stage=ArtifactFolders.BACKEND,
            base_name=ArtifactNames.BACKEND_BLUEPRINT,
            content=response_content,
            ext="md"
        )
        logger.info("Backend artifact created")
        
        # Build state updates
        new_message = AIMessage(
            content=response_content,
            name="backend_engineer"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "backend_engineering_completed": True,
            "last_updated": generate_timestamp()
        }
        
        state_updates = {
            "backend_blueprint": response_content,
            "artifacts": {
                ArtifactFolders.BACKEND: [saved_path]
            },
            "current_stage": WorkflowStages.BACKEND_ENGINEERING,
            "messages": [new_message],
            "metadata": updated_metadata
        }
        
        return state_updates
