"""Conversation Memory Manager."""

import uuid
from typing import Optional, List, Dict, Any
from memory.models import User, Session, ConversationTurn
from memory.storage import MemoryStorage, JSONMemoryStorage
from config.logging import get_logger
from core.utils import generate_timestamp

logger = get_logger("memory.manager")

class ConversationMemoryManager:
    """High-level manager for interacting with Conversation Memory."""
    
    def __init__(self, storage: Optional[MemoryStorage] = None):
        # Default to local JSON storage if none provided
        self.storage = storage or JSONMemoryStorage()
        
    def create_user(self, name: str, user_id: Optional[str] = None) -> User:
        """Create a new user and save to storage."""
        uid = user_id or str(uuid.uuid4())
        user = User(user_id=uid, name=name)
        self.storage.save_user(user)
        logger.info(f"Created new user: {name} ({uid})")
        return user
        
    def get_user(self, user_id: str) -> Optional[User]:
        """Fetch an existing user."""
        return self.storage.get_user(user_id)
        
    def create_session(self, user_id: str, session_id: Optional[str] = None) -> Session:
        """Create a new session for a user."""
        if not self.get_user(user_id):
            raise ValueError(f"Cannot create session: User {user_id} does not exist.")
            
        sid = session_id or str(uuid.uuid4())
        session = Session(session_id=sid, user_id=user_id)
        self.storage.save_session(session)
        logger.info(f"Created new session {sid} for user {user_id}")
        return session
        
    def get_session(self, session_id: str) -> Optional[Session]:
        """Fetch an existing session."""
        return self.storage.get_session(session_id)
        
    def add_turn_to_session(
        self,
        session_id: str,
        prompt: str,
        intent: Optional[Dict[str, Any]] = None,
        execution_plan: Optional[List[str]] = None,
        artifacts: Optional[Dict[str, List[str]]] = None,
        final_state_summary: Optional[Dict[str, Any]] = None
    ) -> ConversationTurn:
        """Record a single interaction turn to a session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} does not exist.")
            
        turn_id = str(uuid.uuid4())
        turn = ConversationTurn(
            turn_id=turn_id,
            prompt=prompt,
            intent=intent,
            execution_plan=execution_plan,
            artifacts=artifacts or {},
            final_state_summary=final_state_summary or {}
        )
        
        session.turns.append(turn)
        self.storage.save_session(session)
        logger.info(f"Added turn {turn_id} to session {session_id}")
        return turn
        
    def get_conversation_history(self, session_id: str) -> List[ConversationTurn]:
        """Fetch the full sequence of interaction turns for a session."""
        session = self.get_session(session_id)
        if not session:
            return []
        return session.turns
