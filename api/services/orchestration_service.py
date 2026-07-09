"""Orchestration service layer bridging FastAPI to the LangGraph workflow."""

import asyncio
import uuid
from typing import Dict, Any, Optional, List, cast
from app.state import ForgeState
from app.dynamic_graph import DynamicWorkflowOrchestrator
from core.constants import ApprovalStatuses
from core.utils import generate_timestamp
from core.feedback.manager import FeedbackManager
from core.feedback.art_plugin import ARTPluginInterface
from agents.feedback_agent.agent import StubARTPlugin
from memory.manager import ConversationMemoryManager

# In-memory execution store for API backward compatibility/state retrieval
_EXECUTION_STORE: Dict[str, ForgeState] = {}

class OrchestrationService:
    """Service to safely execute dynamic workflows outside of the CLI context."""
    
    def __init__(self):
        self.orchestrator = DynamicWorkflowOrchestrator()
        self.feedback_manager = FeedbackManager(art_plugin=StubARTPlugin())
        self.memory_manager = ConversationMemoryManager()
        
    def _prepare_memory_context(self, state: ForgeState, user_id: Optional[str], session_id: Optional[str]) -> ForgeState:
        if not user_id or not session_id:
            return state
            
        user = self.memory_manager.get_user(user_id)
        if not user:
            self.memory_manager.create_user(name=f"User {user_id}", user_id=user_id)
            
        session = self.memory_manager.get_session(session_id)
        if not session:
            self.memory_manager.create_session(user_id=user_id, session_id=session_id)
            
        history = self.memory_manager.get_conversation_history(session_id)
        if history:
            state["conversation_history"] = [
                {
                    "turn_id": turn.turn_id,
                    "prompt": turn.prompt,
                    "intent": turn.intent,
                    "timestamp": turn.timestamp
                } for turn in history
            ]
            
            last_turn = history[-1]
            if last_turn.architecture_version:
                state["previous_architecture"] = last_turn.architecture_version
            if last_turn.diagram_versions:
                state["previous_diagrams"] = last_turn.diagram_versions
                
        return state
        
    def _save_memory_turn(self, session_id: Optional[str], prompt: str, final_state: ForgeState) -> None:
        if not session_id:
            return
            
        self.memory_manager.add_turn_to_session(
            session_id=session_id,
            prompt=prompt,
            intent=final_state.get("metadata", {}).get("intent"),
            execution_plan=final_state.get("metadata", {}).get("execution_plan"),
            architecture_version=final_state.get("architecture_json"),
            diagram_versions=final_state.get("plantuml_diagrams"),
            artifacts=final_state.get("artifacts")
        )
        
    def _create_base_state(self, prompt: str) -> ForgeState:
        """Create a foundational state dict without CLI assumptions."""
        # pyrefly: ignore [bad-return-type]
        return {
            "user_request": prompt,
            "current_stage": "",
            "approval_status": ApprovalStatuses.PENDING,
            "approval_history": [],
            "requirements": None,
            "architecture": None,
            "backend_blueprint": None,
            "implementation": None,
            "qa_report": None,
            "security_report": None,
            "review_report": None,
            "deployment_blueprint": None,
            "generated_files": {},
            "artifacts": {},
            "messages": [],
            "metadata": {
                "started_at": generate_timestamp(),
            },
            "qa_score": None,
            "security_score": None,
            "review_score": None,
            "quality_weights": None,
            "overall_quality_score": None,
            "deployment_status": None,
            "validation_summary": None,
            "quality_report": None,
            "quality_gate_status": None,
            "reasoning_logs": [],
            "timeline_events": [],
            "execution_timeline": None,
            "workflow_start_time": None,
            "workflow_end_time": None,
            "production_readiness_report": None,
            "production_readiness_score": None,
            "final_report": None,
            "project_status": None,
            "generated_artifacts_count": None,
            "generated_files_count": None,
            "workflow_execution_time": None,
            "agents_executed": None,
            "parallel_executions": None,
            "approval_gates_completed": None,
            "estimated_time_saved": None,
            "execution_report": None,
            "impact_analysis_report": None,
            "user_feedback": None,
            "uml_recommendation_report": None,
            "requirements_json": None,
            "architecture_json": None,
            "selected_uml_diagrams": None,
            "plantuml_diagrams": None,
            "plantuml_validation_report": None,
            "rendered_svg_references": None,
            "conversation_history": None,
            "previous_architecture": None,
            "previous_diagrams": None
        }
        
    def generate_architecture(
        self, 
        prompt: str, 
        diagram_types: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a full Generation workflow."""
        state = self._create_base_state(prompt)
        state = self._prepare_memory_context(state, user_id, session_id)
        
        # Inject optional constraints
        if diagram_types:
            state["metadata"]["requested_diagrams"] = diagram_types
            
        final_state = self.orchestrator.execute_workflow(state)
        self._save_memory_turn(session_id, prompt, final_state)
        
        # Save to memory store
        report = final_state.get("execution_report") or {}
        execution_id = report.get("execution_id", str(uuid.uuid4()))
        _EXECUTION_STORE[execution_id] = final_state
        
        return {
            "execution_id": execution_id,
            "requirements": final_state.get("requirements_json"),
            "architecture": final_state.get("architecture_json"),
            "selected_diagrams": final_state.get("selected_uml_diagrams", []),
            "plantuml": final_state.get("plantuml_diagrams", {}),
            "validation": final_state.get("plantuml_validation_report", {}),
            "rendered_artifacts": final_state.get("rendered_svg_references", {}),
            "execution_metadata": report
        }
        
    def update_architecture(
        self, 
        prompt: str, 
        execution_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute an Update workflow with Impact Analysis."""
        state = self._create_base_state(prompt)
        state = self._prepare_memory_context(state, user_id, session_id)
        
        # If execution_id is provided and found, carry over previous architecture context
        if execution_id and execution_id in _EXECUTION_STORE:
            prev_state = _EXECUTION_STORE[execution_id]
            state["architecture_json"] = prev_state.get("architecture_json")
            state["selected_uml_diagrams"] = prev_state.get("selected_uml_diagrams", [])
            
        final_state = self.orchestrator.execute_workflow(state)
        self._save_memory_turn(session_id, prompt, final_state)
        
        report = final_state.get("execution_report") or {}
        new_execution_id = report.get("execution_id", str(uuid.uuid4()))
        _EXECUTION_STORE[new_execution_id] = final_state
        
        impact = final_state.get("impact_analysis_report") or {}
        
        return {
            "affected_diagrams": impact.get("affected_diagrams", []),
            "reused_diagrams": impact.get("reuse_diagrams", []),
            "updated_artifacts": final_state.get("rendered_svg_references", {})
        }
        
    def submit_feedback(self, execution_id: str, feedback: str, user_id: str = "api_user") -> Dict[str, Any]:
        """Submit feedback, skipping standard orchestration directly via FeedbackManager."""
        prev_state = _EXECUTION_STORE.get(execution_id, {})
        prompt = prev_state.get("user_request") or ""
        architecture = cast(Dict[str, Any], prev_state.get("architecture_json") or {})
        plantuml = cast(Dict[str, str], prev_state.get("plantuml_diagrams") or {})
        reasoning = cast(List[Dict[str, Any]], prev_state.get("reasoning_logs") or [])
        execution_metadata = cast(Dict[str, Any], prev_state.get("execution_report") or {})
        
        self.feedback_manager.submit_feedback(
            user_id=user_id,
            project_id="forgeai_api",
            prompt=prompt,
            architecture=architecture,
            generated_uml=plantuml,
            user_feedback=feedback,
            reasoning=reasoning,
            execution_metadata=execution_metadata
        )
        
        return {
            "status": "stored",
            "art_plugin": "processed"
        }
        
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve execution metadata."""
        if execution_id not in _EXECUTION_STORE:
            return None
            
        state = _EXECUTION_STORE[execution_id]
        report = state.get("execution_report") or {}
        
        return {
            "execution_id": execution_id,
            "agents_executed": report.get("agents_executed", []),
            "llm_calls": report.get("llm_calls", 0),
            "execution_time_ms": report.get("execution_time_ms", 0),
            "validation_retries": report.get("validation_retries", 0),
            "artifacts_generated": report.get("artifacts", {})
        }
