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
        architecture: Dict[str, Any],
        generated_uml: Dict[str, str],
        user_feedback: str,
        reasoning: List[Dict[str, Any]],
        execution_metadata: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserFeedbackEntry:
        """
        Record user feedback on a generated UML diagram.
        Saves to storage, forwards to the ART Plugin, and creates a training dataset.
        """
        entry_id = str(uuid.uuid4())
        entry = UserFeedbackEntry(
            feedback_id=entry_id,
            user_id=user_id,
            project_id=project_id,
            prompt=prompt,
            architecture=architecture,
            generated_uml=generated_uml,
            user_feedback=user_feedback,
            reasoning=reasoning,
            execution_metadata=execution_metadata,
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
                
        # 3. Create structured training dataset
        import os
        import json
        from app.settings import settings
        from core.utils import ensure_directory
        
        dataset_dir = os.path.join(settings.ARTIFACT_ROOT, "training")
        ensure_directory(dataset_dir)
        dataset_path = os.path.join(dataset_dir, "feedback_dataset.jsonl")
        
        record = {
            "feedback_id": entry_id,
            "prompt": prompt,
            "architecture": architecture,
            "uml": generated_uml,
            "feedback": user_feedback,
            "reasoning": reasoning,
            "execution_metadata": execution_metadata,
            "timestamp": entry.timestamp
        }
        
        try:
            with open(dataset_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\\n")
            logger.info(f"Appended feedback {entry_id} to training dataset.")
        except Exception as e:
            logger.error(f"Failed to append to training dataset: {e}")
                
        return entry
