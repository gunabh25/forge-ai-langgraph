"""Execution Timeline Engine for tracking and formatting workflow events."""

from typing import Dict, Any, List
from core.workflow_events import WorkflowEventManager, EventTypes
from core.utils import generate_timestamp
from core.constants import ArtifactNames, ArtifactFolders
from core.artifact_manager import ArtifactManager

class TimelineEngine:
    """Subscribes to events and generates the Execution Timeline."""

    def __init__(self):
        self.event_manager = WorkflowEventManager()
        self.events: List[Dict[str, Any]] = []
        
        # Subscribe to relevant events
        self.event_manager.subscribe(EventTypes.WORKFLOW_STARTED, self._on_workflow_started)
        self.event_manager.subscribe(EventTypes.AGENT_STARTED, self._on_agent_started)
        self.event_manager.subscribe(EventTypes.AGENT_COMPLETED, self._on_agent_completed)
        self.event_manager.subscribe(EventTypes.ARTIFACT_GENERATED, self._on_artifact_generated)
        self.event_manager.subscribe(EventTypes.APPROVAL_REQUESTED, self._on_approval_requested)
        self.event_manager.subscribe(EventTypes.APPROVAL_COMPLETED, self._on_approval_completed)
        self.event_manager.subscribe(EventTypes.WORKFLOW_COMPLETED, self._on_workflow_completed)
        self.event_manager.subscribe(EventTypes.WORKFLOW_FAILED, self._on_workflow_failed)
        
    def _add_event(self, emoji: str, description: str, payload: Dict[str, Any]):
        event = {
            "timestamp": generate_timestamp(),
            "emoji": emoji,
            "description": description,
            "event_type": payload.get("event_type")
        }
        self.events.append(event)
        
        # In a real system, we'd also push this to state, but for decoupled architecture,
        # we let it sit in the singleton until completion.
        
    def _on_workflow_started(self, payload: Dict[str, Any]):
        self._add_event("🚀", "Workflow Started", payload)

    def _on_agent_started(self, payload: Dict[str, Any]):
        agent_name = payload.get("stage", "Agent").replace("_", " ").title()
        self._add_event("🟢", f"{agent_name} Started", payload)

    def _on_agent_completed(self, payload: Dict[str, Any]):
        agent_name = payload.get("stage", "Agent").replace("_", " ").title()
        
        # Differentiate between normal and validation agents
        if payload.get("stage") in ["qa_testing", "security_audit", "code_review"]:
            self._add_event("⚡", f"{agent_name} Completed", payload)
        else:
            self._add_event("✅", f"{agent_name} Completed", payload)

    def _on_artifact_generated(self, payload: Dict[str, Any]):
        artifact_name = payload.get("base_name", "Artifact").replace("_", " ").title()
        # To avoid duplicating agent completed log, we just log artifact creation
        self._add_event("📄", f"{artifact_name} Generated", payload)

    def _on_approval_requested(self, payload: Dict[str, Any]):
        self._add_event("⏳", "Waiting for Human Approval", payload)

    def _on_approval_completed(self, payload: Dict[str, Any]):
        decision = payload.get("decision", "unknown")
        self._add_event("👤", f"Human Approval Completed ({decision})", payload)

    def _on_workflow_completed(self, payload: Dict[str, Any]):
        self._add_event("🎉", "ForgeAI Completed", payload)
        self._generate_timeline_artifact(payload.get("state", {}))
        
    def _on_workflow_failed(self, payload: Dict[str, Any]):
        self._add_event("❌", f"Workflow Failed: {payload.get('error')}", payload)
        self._generate_timeline_artifact(payload.get("state", {}))

    def _generate_timeline_artifact(self, state: Dict[str, Any]):
        """Generates the markdown timeline and saves it."""
        lines = [
            "================================================",
            "Execution Timeline",
            "================================================"
        ]
        
        for event in self.events:
            # Extract time component: YYYY-MM-DDTHH:MM:SSZ -> HH:MM:SS
            ts = event["timestamp"]
            time_part = ts.split("T")[1][:8] if "T" in ts else ts
            lines.append(f"{time_part}  {event['emoji']} {event['description']}")
            
        lines.append("================================================")
        
        content = "\n".join(lines)
        
        if state:
            # Optionally update state
            state["execution_timeline"] = content
            
        artifact_manager = ArtifactManager()
        artifact_manager.save_artifact(
            stage=ArtifactFolders.TIMELINE,
            base_name=ArtifactNames.EXECUTION_TIMELINE,
            content=content,
            ext="md"
        )
