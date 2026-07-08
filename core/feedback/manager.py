"""Feedback Manager architectural orchestrator."""

import uuid
from typing import Optional, List, Dict, Any
from config.logging import get_logger
from core.feedback.models import UserFeedbackEntry
from core.feedback.storage import FeedbackStorageInterface
from core.feedback.art_plugin import ARTPluginInterface

logger = get_logger("core.feedback.manager")

class FeedbackManager:
    """
    Manages the lifecycle of user feedback, storage, and ART plugin integration.
    """
    
    def __init__(
        self, 
        storage: Optional[FeedbackStorageInterface] = None,
        art_plugin: Optional[ARTPluginInterface] = None
    ):
        self.storage = storage
        self.art_plugin = art_plugin
        
    def submit_feedback(
        self,
        user_id: str,
        project_id: str,
        prompt: str,
        generated_uml: str,
        user_feedback: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserFeedbackEntry:
        """
        Record user feedback on a generated UML diagram.
        Saves to storage and forwards to the ART Plugin if configured.
        """
        entry_id = str(uuid.uuid4())
        entry = UserFeedbackEntry(
            feedback_id=entry_id,
            user_id=user_id,
            project_id=project_id,
            prompt=prompt,
            generated_uml=generated_uml,
            user_feedback=user_feedback,
            metadata=metadata or {}
        )
        
        # 1. Persist to storage
        if self.storage:
            self.storage.save_feedback(entry)
            logger.info(f"Saved feedback {entry_id} for user {user_id}")
        else:
            logger.warning("FeedbackManager: No storage configured. Feedback not persisted.")
            
        # 2. Forward to ART Plugin
        if self.art_plugin:
            try:
                self.art_plugin.process_feedback(entry)
                logger.info(f"Forwarded feedback {entry_id} to ART plugin.")
            except Exception as e:
                logger.error(f"ART plugin failed to process feedback {entry_id}: {e}")
                
        return entry
