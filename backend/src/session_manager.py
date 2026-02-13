"""
Session Management

Provides session tracking and action logging for chat sessions.
"""

from datetime import datetime
from typing import Dict, List, Optional
import json
import os
import uuid

PERSIST_PATH = os.path.join(os.path.dirname(__file__), "../db/sessions.json")


class ChatSession:
    """Represents a chat session with message and action history."""
    
    def __init__(self, user_id: str = "default", provider: str = "copilot", settings: Optional[Dict] = None):
        self.session_id = str(uuid.uuid4())
        self.user_id = user_id
        self.provider = provider
        self.start_time = datetime.now()
        self.end_time = None
        self.messages = []
        self.actions = []
        self.settings = settings or {"verbose": False}
    
    def add_message(self, sender: str, content: str, action_taken: Optional[str] = None):
        """Add a message to the session."""
        message = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": sender,
            "content": content,
            "action_taken": action_taken
        }
        self.messages.append(message)
        if action_taken:
            self.add_action(action_taken, "completed")
        return message

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "provider": self.provider,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "messages": self.messages,
            "actions": self.actions,
            "settings": self.settings
        }

    @staticmethod
    def from_dict(data: dict) -> "ChatSession":
        session = ChatSession(
            user_id=data.get("user_id", "default"),
            provider=data.get("provider", "copilot"),
            settings=data.get("settings")
        )
        session.session_id = data.get("session_id", session.session_id)
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        if start_time:
            session.start_time = datetime.fromisoformat(start_time)
        if end_time:
            session.end_time = datetime.fromisoformat(end_time)
        session.messages = data.get("messages", [])
        session.actions = data.get("actions", [])
        return session
    
    def add_action(self, action_type: str, status: str = "pending", permission_requested: bool = False, permission_granted: bool = False):
        """Log an action in this session."""
        action = {
            "id": str(uuid.uuid4()),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "status": status,
            "permission_requested": permission_requested,
            "permission_granted": permission_granted
        }
        self.actions.append(action)
        return action
    
    def get_history(self):
        """Get chat history for this session."""
        return self.messages
    
    def get_actions(self):
        """Get action log for this session."""
        return self.actions
    
    def close(self):
        """Close the session."""
        self.end_time = datetime.now()


class SessionManager:
    """Manages all active chat sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self._load()

    def _load(self):
        if not os.path.exists(PERSIST_PATH):
            return
        try:
            with open(PERSIST_PATH, "r") as f:
                data = json.load(f)
            sessions = data.get("sessions", [])
            for item in sessions:
                session = ChatSession.from_dict(item)
                self.sessions[session.session_id] = session
        except Exception:
            # If persistence fails, start with a clean in-memory store.
            self.sessions = {}

    def _save(self):
        os.makedirs(os.path.dirname(PERSIST_PATH), exist_ok=True)
        payload = {
            "sessions": [s.to_dict() for s in self.sessions.values()]
        }
        with open(PERSIST_PATH, "w") as f:
            json.dump(payload, f, indent=2)
    
    def create_session(self, user_id: str = "default", provider: str = "copilot") -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(user_id=user_id, provider=provider)
        self.sessions[session.session_id] = session
        self._save()
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    def add_message_to_session(self, session_id: str, sender: str, content: str, action_taken: Optional[str] = None):
        """Add a message to a session."""
        session = self.get_session(session_id)
        if session:
            message = session.add_message(sender, content, action_taken)
            self._save()
            return message
        return None
    
    def add_action_to_session(self, session_id: str, action_type: str, status: str = "pending", 
                            permission_requested: bool = False, permission_granted: bool = False):
        """Log an action in a session."""
        session = self.get_session(session_id)
        if session:
            action = session.add_action(action_type, status, permission_requested, permission_granted)
            self._save()
            return action
        return None
    
    def get_session_history(self, session_id: str) -> List[dict]:
        """Get the message history of a session."""
        session = self.get_session(session_id)
        if session:
            return session.get_history()
        return []
    
    def get_session_actions(self, session_id: str) -> List[dict]:
        """Get the action log of a session."""
        session = self.get_session(session_id)
        if session:
            return session.get_actions()
        return []
    
    def get_all_actions(self) -> List[dict]:
        """Get all actions from all sessions."""
        all_actions = []
        for session in self.sessions.values():
            all_actions.extend(session.get_actions())
        return all_actions

    def list_sessions(self) -> List[dict]:
        """List sessions with basic metadata."""
        sessions = []
        for session in self.sessions.values():
            if session.end_time:
                continue
            sessions.append({
                "session_id": session.session_id,
                "user_id": session.user_id,
                "provider": session.provider,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "message_count": len(session.messages)
            })
        sessions.sort(key=lambda s: s.get("start_time", ""), reverse=True)
        return sessions
    
    def close_session(self, session_id: str):
        """Close a session."""
        session = self.get_session(session_id)
        if session:
            session.close()
            self._save()


# Singleton session manager
session_manager = SessionManager()
