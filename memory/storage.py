"""Storage abstractions for Conversation Memory."""

import json
import os
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from memory.models import User, Session, ConversationTurn
import dataclasses

class MemoryStorage(ABC):
    """Abstract Base Class for Conversation Memory storage."""
    
    @abstractmethod
    def save_user(self, user: User) -> None:
        pass
        
    @abstractmethod
    def get_user(self, user_id: str) -> Optional[User]:
        pass
        
    @abstractmethod
    def save_session(self, session: Session) -> None:
        pass
        
    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Session]:
        pass
        
    @abstractmethod
    def list_user_sessions(self, user_id: str) -> List[str]:
        pass

class EnhancedJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles dataclasses."""
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)

class JSONMemoryStorage(MemoryStorage):
    """Concrete implementation of MemoryStorage using local JSON files."""
    
    def __init__(self, base_dir: str = ".forge_memory"):
        self.base_dir = base_dir
        self.users_dir = os.path.join(self.base_dir, "users")
        self.sessions_dir = os.path.join(self.base_dir, "sessions")
        
        os.makedirs(self.users_dir, exist_ok=True)
        os.makedirs(self.sessions_dir, exist_ok=True)
        
    def _user_path(self, user_id: str) -> str:
        return os.path.join(self.users_dir, f"{user_id}.json")
        
    def _session_path(self, session_id: str) -> str:
        return os.path.join(self.sessions_dir, f"{session_id}.json")
        
    def save_user(self, user: User) -> None:
        with open(self._user_path(user.user_id), 'w', encoding='utf-8') as f:
            json.dump(user, f, cls=EnhancedJSONEncoder, indent=2)
            
    def get_user(self, user_id: str) -> Optional[User]:
        path = self._user_path(user_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return User(**data)
            
    def save_session(self, session: Session) -> None:
        with open(self._session_path(session.session_id), 'w', encoding='utf-8') as f:
            json.dump(session, f, cls=EnhancedJSONEncoder, indent=2)
            
    def get_session(self, session_id: str) -> Optional[Session]:
        path = self._session_path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Reconstruct turns
            turns_data = data.pop("turns", [])
            turns = [ConversationTurn(**t) for t in turns_data]
            return Session(**data, turns=turns)
            
    def list_user_sessions(self, user_id: str) -> List[str]:
        # Simple scan of sessions to find those matching user_id
        user_sessions = []
        for filename in os.listdir(self.sessions_dir):
            if filename.endswith(".json"):
                with open(os.path.join(self.sessions_dir, filename), 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        if data.get("user_id") == user_id:
                            user_sessions.append(data.get("session_id"))
                    except json.JSONDecodeError:
                        continue
        return user_sessions
