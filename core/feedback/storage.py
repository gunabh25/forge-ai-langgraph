"""Storage abstractions for Feedback Manager."""

from abc import ABC, abstractmethod
from typing import List, Optional
from core.feedback.models import UserFeedbackEntry

class FeedbackStorageInterface(ABC):
    """Abstract interface for persisting User Feedback."""
    
    @abstractmethod
    def save_feedback(self, entry: UserFeedbackEntry) -> None:
        pass
        
    @abstractmethod
    def get_feedback(self, feedback_id: str) -> Optional[UserFeedbackEntry]:
        pass
        
    @abstractmethod
    def get_feedback_by_project(self, project_id: str) -> List[UserFeedbackEntry]:
        pass
        
    @abstractmethod
    def get_feedback_by_user(self, user_id: str) -> List[UserFeedbackEntry]:
        pass
