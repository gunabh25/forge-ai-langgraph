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
            if last_turn.requirements_version:
                state["previous_requirements"] = last_turn.requirements_version
            if last_turn.architecture_version:
                state["previous_architecture"] = last_turn.architecture_version
            if last_turn.diagram_versions:
                state["previous_diagrams"] = last_turn.diagram_versions
            if last_turn.selected_uml_diagrams_version:
                state["previous_selected_uml_diagrams"] = last_turn.selected_uml_diagrams_version
            if last_turn.diagram_execution_states_version:
                state["previous_diagram_execution_states"] = last_turn.diagram_execution_states_version
                
            arch_history = []
            for turn in history:
                if turn.architecture_version:
                    arch_history.append(turn.architecture_version)
            state["architecture_history"] = arch_history
                
        return state
        
    def _save_memory_turn(self, session_id: Optional[str], prompt: str, final_state: ForgeState) -> None:
        if not session_id:
            return
            
        self.memory_manager.add_turn_to_session(
            session_id=session_id,
            prompt=prompt,
            intent=final_state.get("metadata", {}).get("intent"),
            execution_plan=final_state.get("metadata", {}).get("execution_plan"),
            requirements_version=final_state.get("requirements_json"),
            architecture_version=final_state.get("architecture_json"),
            diagram_versions=final_state.get("plantuml_diagrams"),
            selected_uml_diagrams_version=final_state.get("selected_uml_diagrams"),
            diagram_execution_states_version=final_state.get("diagram_execution_states"),
            artifacts=final_state.get("artifacts"),
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
            "execution_report": {},
            "impact_analysis_report": None,
            "user_feedback": None,
            "uml_recommendation_report": None,
            "requirements_json": None,
            "architecture_json": None,
            "architecture_summary": None,
            "selected_uml_diagrams": None,
            "plantuml_diagrams": None,
            "plantuml_validation_report": None,
            "rendered_svg_references": None,
            "conversation_history": None,
            "previous_requirements": None,
            "previous_architecture": None,
            "previous_diagrams": None,
            "previous_selected_uml_diagrams": None,
            "previous_diagram_execution_states": None,
            "diagram_execution_states": {},
            "current_diagram_id": None,
            "workflow_execution_summary": None,
            "execution_strategy": None,
            "change_analysis_report": None,
            "architecture_history": []
        }
        
    def generate_architecture(
        self, 
        prompt: str, 
        diagram_types: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a full Generation workflow."""
        import time
        from core.workflow_events import WorkflowEventManager, EventTypes
        import core.context as ctx
        
        workflow_id = str(uuid.uuid4())
        ctx.workflow_id_var.set(workflow_id)
        if session_id:
            ctx.session_id_var.set(session_id)
        if user_id:
            ctx.user_id_var.set(user_id)
            
        WorkflowEventManager().publish(EventTypes.WORKFLOW_STARTED, {
            "workflow_id": workflow_id,
            "timestamp": time.time(),
            "request": prompt
        })
        
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
        
        WorkflowEventManager().publish(EventTypes.WORKFLOW_COMPLETED, {
            "workflow_id": workflow_id,
            "timestamp": time.time(),
            "execution_id": execution_id
        })
        
        return {
            "execution_id": execution_id,
            "user_id": user_id,
            "requirements": final_state.get("requirements_json") or {},
            "architecture": final_state.get("architecture_json") or {},
            "selected_diagrams": final_state.get("selected_uml_diagrams", []),
            "plantuml": final_state.get("plantuml_diagrams", {}),
            "validation_reports": final_state.get("plantuml_validation_report", {}),
            "rendered_artifacts": final_state.get("rendered_svg_references", {}),
            "execution_metadata": report,
            "execution_metrics": report.get("metrics", {}),
            "artifacts": final_state.get("artifacts", {})
        }
        
    def update_architecture(
        self, 
        prompt: str, 
        execution_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute an Update workflow with Impact Analysis."""
        import time
        from core.workflow_events import WorkflowEventManager, EventTypes
        import core.context as ctx
        
        workflow_id = str(uuid.uuid4())
        ctx.workflow_id_var.set(workflow_id)
        if session_id:
            ctx.session_id_var.set(session_id)
        if user_id:
            ctx.user_id_var.set(user_id)
            
        WorkflowEventManager().publish(EventTypes.WORKFLOW_STARTED, {
            "workflow_id": workflow_id,
            "timestamp": time.time(),
            "request": prompt
        })
        
        state = self._create_base_state(prompt)
        state = self._prepare_memory_context(state, user_id, session_id)
        
        # If execution_id is provided and found, carry over previous architecture context
        if execution_id and execution_id in _EXECUTION_STORE:
            prev_state = _EXECUTION_STORE[execution_id]
            state["architecture_json"] = prev_state.get("architecture_json")
            state["selected_uml_diagrams"] = prev_state.get("selected_uml_diagrams", [])
            state["plantuml_diagrams"] = prev_state.get("plantuml_diagrams", {})
            state["rendered_svg_references"] = prev_state.get("rendered_svg_references", {})
            
        final_state = self.orchestrator.execute_workflow(state)
        self._save_memory_turn(session_id, prompt, final_state)
        
        report = final_state.get("execution_report") or {}
        new_execution_id = report.get("execution_id", str(uuid.uuid4()))
        _EXECUTION_STORE[new_execution_id] = final_state
        
        impact = final_state.get("impact_analysis_report") or {}
        
        WorkflowEventManager().publish(EventTypes.WORKFLOW_COMPLETED, {
            "workflow_id": workflow_id,
            "timestamp": time.time(),
            "execution_id": new_execution_id
        })
        
        return {
            "execution_id": new_execution_id,
            "affected_diagrams": impact.get("affected_diagrams", []),
            "reused_diagrams": impact.get("reuse_diagrams", []),
            "updated_artifacts": final_state.get("rendered_svg_references", {}),
            "execution_metadata": report,
            "artifacts": final_state.get("artifacts", {}),
            "validation_reports": final_state.get("plantuml_validation_report", {}),
            "execution_metrics": report.get("metrics", {})
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
            "art_plugin": "processed",
            "execution_metadata": execution_metadata,
            "artifacts": {},
            "validation_reports": {},
            "execution_metrics": {}
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
            "artifacts_generated": report.get("artifacts", {}),
            
            # Observability fields
            "execution_graph": state.get("metadata", {}).get("execution_plan"),
            "execution_timeline": state.get("timeline_events"),
            "reasoning": state.get("reasoning_logs"),
            "generated_diagrams": {
                "plantuml": state.get("plantuml_diagrams"),
                "rendered_svgs": state.get("rendered_svg_references")
            },
            "validation_reports": {
                "qa_report": state.get("qa_report"),
                "security_report": state.get("security_report"),
                "review_report": state.get("review_report"),
                "validation_summary": state.get("validation_summary"),
                "quality_report": state.get("quality_report")
            },
            "rendered_artifacts": state.get("rendered_svg_references", {}),
            "execution_metadata": report,
            "artifacts": state.get("artifacts", {}),
            "execution_metrics": report.get("metrics", {})
        }

    def replay_execution(self, execution_id: str, start_stage: Optional[str] = None) -> Dict[str, Any]:
        """Replay a workflow execution from a previous state."""
        if execution_id not in _EXECUTION_STORE:
            raise ValueError(f"Execution ID {execution_id} not found.")
            
        old_state = _EXECUTION_STORE[execution_id].copy()
        
        # Reset properties that should be regenerated on replay
        old_state["approval_status"] = ApprovalStatuses.PENDING
        old_state["current_stage"] = start_stage if start_stage else ""
        if "metadata" in old_state:
            old_state["metadata"]["started_at"] = generate_timestamp()
            
        final_state = self.orchestrator.execute_workflow(old_state)
        
        new_execution_id = final_state.get("execution_report", {}).get("execution_id", str(uuid.uuid4()))
        _EXECUTION_STORE[new_execution_id] = final_state
        
        return self.get_execution(new_execution_id) # type: ignore

    def get_artifact_path(self, execution_id: str, artifact_path: str) -> Optional[str]:
        """Resolve an artifact path securely for a given execution."""
        if execution_id not in _EXECUTION_STORE:
            return None
            
        state = _EXECUTION_STORE[execution_id]
        
        # We need to verify if the artifact exists in the state's artifacts or diagrams
        all_artifacts = []
        artifacts = state.get("artifacts") or {}
        for artifact_list in artifacts.values():
            all_artifacts.extend(artifact_list)
            
        svg_refs = state.get("rendered_svg_references") or {}
        for svg_path in svg_refs.values():
            all_artifacts.append(svg_path)
            
        # Match against absolute path or suffix
        import os
        for saved_path in all_artifacts:
            if saved_path == artifact_path or saved_path.endswith(artifact_path):
                if os.path.exists(saved_path):
                    return saved_path
                    
        return None
        
    def get_metrics(self) -> Dict[str, Any]:
        """Calculate global metrics across all executions."""
        total = len(_EXECUTION_STORE)
        successful = 0
        failed = 0
        total_latency = 0
        total_llm_calls = 0
        diagrams_rendered = 0
        
        for state in _EXECUTION_STORE.values():
            report = state.get("execution_report") or {}
            
            # Count success/failure
            if report.get("workflow_status") == "failed":
                failed += 1
            else:
                successful += 1
                
            total_latency += report.get("execution_time_ms", 0)
            total_llm_calls += report.get("llm_calls", 0)
            
            rendered = state.get("rendered_svg_references") or {}
            diagrams_rendered += len(rendered)
            
        avg_latency = total_latency / total if total > 0 else 0.0
        
        return {
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "average_latency_ms": avg_latency,
            "total_llm_calls": total_llm_calls,
            "diagrams_rendered": diagrams_rendered
        }
