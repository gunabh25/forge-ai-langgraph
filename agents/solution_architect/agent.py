"""Solution Architect Agent implementation."""

from typing import Dict, Any, Optional, List
from agents.base import BaseAgent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from core.llm import get_llm
from core.prompts import load_prompt, load_examples
from app.state import ForgeState
from config.logging import get_logger
from core.constants import WorkflowStages, ApprovalStatuses, ArtifactFolders, ArtifactNames
from core.utils import generate_timestamp
from core.artifact_manager import ArtifactManager

logger = get_logger("agents.solution_architect")

class SolutionArchitectAgent(BaseAgent):
    """Solution Architect agent responsible for generating the Architecture Specification."""
    
    @property
    def name(self) -> str:
        return "Solution Architect"
        
    @property
    def description(self) -> str:
        return "Responsible for generating the Architecture Specification."
        
    @property
    def capabilities(self) -> List[str]:
        return ["architecture_design", "system_modeling"]

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm
        self.system_prompt = load_prompt("solution_architect")
        try:
            self.examples = load_examples("solution_architect")
        except FileNotFoundError:
            self.examples = ""
        self.artifact_manager = ArtifactManager()
        
    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm
        
    def run(self, state: ForgeState) -> Dict[str, Any]:
        """Execute the Solution Architect agent step.
        
        Args:
            state: The current shared ForgeState.
            
        Returns:
            Dictionary of state updates.
        """
        logger.info("Architecture generation started")
        
        # pyrefly: ignore [missing-attribute]
        requirements = state.get("requirements", "").strip()
        if not requirements:
            raise ValueError("State validation failed: requirements are missing or empty.")
            
        # Compile prompt content
        prompt_content = self.system_prompt
        if self.examples:
            prompt_content += f"\n\nHere are some examples of the expected architecture specification document:\n{self.examples}"
            
        # Get EM analysis if present
        messages_history = state.get("messages", [])
        em_analysis = ""
        for msg in reversed(messages_history):
            if getattr(msg, "name", "") == "engineering_manager":
                em_analysis = msg.content
                break
                
        # Construct messages
        human_content = f"Requirements Specification:\n{requirements}"
        if em_analysis:
            human_content += f"\n\nEngineering Manager Initial Context & Guidance:\n{em_analysis}"
            
        # Check for changes requested feedback
        approval_history = state.get("approval_history", [])
        if approval_history:
            latest_approval = approval_history[-1]
            if latest_approval.get("decision") == ApprovalStatuses.CHANGES_REQUESTED:
                feedback = latest_approval.get("feedback")
                logger.info(f"Retrying architecture generation with human feedback: {feedback}")
                human_content += f"\n\n⚠️ REVISION REQUESTED BY USER:\n{feedback}\n\nPlease revise the architecture specification addressing this feedback."
            
        messages = [
            SystemMessage(content=prompt_content),
            HumanMessage(content=human_content)
        ]
        
        logger.info("Invoking LLM for Solution Architect design...")
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
            stage=ArtifactFolders.ARCHITECTURE,
            base_name=ArtifactNames.ARCHITECTURE,
            content=response_content,
            ext="md"
        )
        logger.info("Architecture artifact created")
        
        # Build state updates
        new_message = AIMessage(
            content=response_content,
            name="solution_architect"
        )
        
        current_metadata = state.get("metadata", {}) or {}
        updated_metadata = {
            **current_metadata,
            "solution_architecture_completed": True,
            "last_updated": generate_timestamp()
        }
        
        state_updates = {
            "architecture": response_content,
            "artifacts": {
                ArtifactFolders.ARCHITECTURE: [saved_path]
            },
            "current_stage": WorkflowStages.SOLUTION_ARCHITECTURE,
            "messages": [new_message],
            "metadata": updated_metadata
        }
        
        logger.info("Architecture completed")
        return state_updates
