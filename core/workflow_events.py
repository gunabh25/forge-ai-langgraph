"""Workflow Event Manager for live streaming and lifecycle events.

Implements a lightweight Pub/Sub system to broadcast events from the LangGraph
workflow to decoupled subscribers like the CLI Dashboard, Timeline Engine,
and Metrics Tracker.
"""

from typing import Callable, Dict, Any, List
from config.logging import get_logger

logger = get_logger("core.workflow_events")


class EventTypes:
    """Standard workflow event types."""
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    
    ARTIFACT_GENERATED = "artifact_generated"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_COMPLETED = "approval_completed"
    
    LLM_INVOKED = "llm_invoked"
    LLM_COMPLETED = "llm_completed"


class WorkflowEventManager:
    """Singleton Pub/Sub manager for workflow events."""
    
    _instance = None
    _subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WorkflowEventManager, cls).__new__(cls)
            cls._subscribers = {
                getattr(EventTypes, k): [] 
                for k in dir(EventTypes) if not k.startswith("__")
            }
            # Also add a catch-all subscriber list
            cls._subscribers["*"] = []
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe a callback to a specific event type.
        
        Args:
            event_type: The event type string (or "*" for all events).
            callback: The function to call when the event is published.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish an event to all registered subscribers.
        
        Args:
            event_type: The type of the event.
            payload: Event data dictionary.
        """
        # Inject the event type into the payload for convenience
        payload["event_type"] = event_type
        
        # Notify specific subscribers
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(payload)
                except Exception as e:
                    logger.error(f"Error in event subscriber for {event_type}: {e}", exc_info=True)
                    
        # Notify wildcard subscribers
        for callback in self._subscribers.get("*", []):
            try:
                callback(payload)
            except Exception as e:
                logger.error(f"Error in wildcard event subscriber: {e}", exc_info=True)
                
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Remove a subscriber."""
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
                
    def clear_subscribers(self) -> None:
        """Clear all subscribers (mainly useful for testing)."""
        for key in self._subscribers:
            self._subscribers[key] = []
