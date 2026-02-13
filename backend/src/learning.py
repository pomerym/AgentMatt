"""
Learning & Memory System

Provides learning and memory management for agent adaptation across sessions.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os
import re
import uuid


class Memory:
    """Represents a learned memory entry."""
    
    def __init__(self, user_id: str, session_id: str, data: Any, category: str = "general"):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.data = data
        self.category = category
        self.learned_at = datetime.now()
        self.last_accessed = None
        self.access_count = 0
        self.relevance_score = 1.0  # Higher = more relevant to recent interactions
    
    def access(self):
        """Record an access to this memory."""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "data": self.data,
            "category": self.category,
            "learned_at": self.learned_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count,
            "relevance_score": self.relevance_score
        }


class MemoryManager:
    """Manages agent learning and memory."""
    
    def __init__(self):
        self.memories: Dict[str, Memory] = {}
        self.user_memories: Dict[str, List[str]] = {}  # user_id -> list of memory_ids
        self.user_profiles: Dict[str, Dict[str, Any]] = {}
        self.persist_path = os.path.join(os.path.dirname(__file__), "../db/memory.json")
        self._load()

    def _load(self):
        if not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r") as f:
                data = json.load(f)
            self.user_memories = data.get("user_memories", {})
            self.user_profiles = data.get("user_profiles", {})
            for item in data.get("memories", []):
                memory = Memory(
                    item.get("user_id", "default"),
                    item.get("session_id", "default"),
                    item.get("data"),
                    item.get("category", "general")
                )
                memory.id = item.get("id", memory.id)
                learned_at = item.get("learned_at")
                last_accessed = item.get("last_accessed")
                if learned_at:
                    memory.learned_at = datetime.fromisoformat(learned_at)
                if last_accessed:
                    memory.last_accessed = datetime.fromisoformat(last_accessed)
                memory.access_count = item.get("access_count", 0)
                memory.relevance_score = item.get("relevance_score", 1.0)
                self.memories[memory.id] = memory
        except Exception:
            self.memories = {}
            self.user_memories = {}
            self.user_profiles = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
        payload = {
            "memories": [m.to_dict() for m in self.memories.values()],
            "user_memories": self.user_memories,
            "user_profiles": self.user_profiles
        }
        with open(self.persist_path, "w") as f:
            json.dump(payload, f, indent=2)
    
    def learn(self, user_id: str, session_id: str, data: Any, category: str = "general") -> Memory:
        """Record new learning from a session."""
        memory = Memory(user_id, session_id, data, category)
        self.memories[memory.id] = memory
        
        # Track memories per user
        if user_id not in self.user_memories:
            self.user_memories[user_id] = []
        self.user_memories[user_id].append(memory.id)
        self._save()
        return memory
    
    def recall(self, user_id: str, query: Optional[str] = None, category: Optional[str] = None, limit: Optional[int] = None) -> List[Memory]:
        """Recall memories for a user, optionally filtered by category."""
        if user_id not in self.user_memories:
            return []
        
        memory_ids = self.user_memories[user_id]
        memories = [self.memories[mid] for mid in memory_ids if mid in self.memories]
        
        # Filter by category if provided
        if category:
            memories = [m for m in memories if m.category == category]

        # Filter by query if provided
        if query:
            q = query.lower()
            memories = [m for m in memories if q in str(m.data).lower()]
        
        # Sort by relevance and recency
        memories.sort(key=lambda m: (-m.relevance_score, -m.access_count))
        
        # Record access
        for memory in memories:
            memory.access()

        if limit:
            memories = memories[:limit]

        self._save()
        return memories

    def search(self, user_id: str, query: str, limit: int = 5) -> List[Memory]:
        """Search memories by query with a simple overlap score."""
        if not query:
            return []
        memories = self.recall(user_id)
        tokens = set(re.findall(r"[a-zA-Z0-9_]+", query.lower()))
        scored = []
        for memory in memories:
            data_text = str(memory.data).lower()
            overlap = sum(1 for t in tokens if t in data_text)
            if overlap:
                scored.append((overlap, memory))
        scored.sort(key=lambda item: (-item[0], -item[1].relevance_score, -item[1].access_count))
        return [m for _, m in scored[:limit]]

    def _contains_sensitive(self, text: str) -> bool:
        if not text:
            return False
        patterns = [
            r"AKIA[0-9A-Z]{16}",
            r"ASIA[0-9A-Z]{16}",
            r"secret",
            r"password",
            r"token",
            r"api[_-]?key",
            r"-----BEGIN"
        ]
        lowered = text.lower()
        return any(re.search(p, text) or p in lowered for p in patterns)

    def maybe_learn_from_message(self, user_id: str, session_id: str, message: str) -> Optional[Memory]:
        """Heuristic learning from user messages while avoiding secrets."""
        if not message or self._contains_sensitive(message):
            return None

        lowered = message.lower()
        triggers = [
            "remember",
            "my name is",
            "i prefer",
            "i like",
            "i dislike",
            "i work on",
            "i am",
            "my project"
        ]
        if not any(t in lowered for t in triggers):
            return None

        memory = self.learn(user_id, session_id, message.strip(), category="preference")
        self.update_profile(user_id)
        return memory

    def update_profile(self, user_id: str) -> Dict[str, Any]:
        """Create a lightweight user profile from memories."""
        existing = self.user_profiles.get(user_id, {})
        adaptation = self.adapt_based_on_memory(user_id)
        profile = {
            "user_id": user_id,
            "preferences": adaptation.get("preferences", {}),
            "patterns": adaptation.get("patterns", []),
            "memory_count": adaptation.get("memory_count", 0),
            "updated_at": datetime.now().isoformat(),
            "approval_scopes": existing.get("approval_scopes", [])
        }
        self.user_profiles[user_id] = profile
        self._save()
        return profile

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the current user profile, if any."""
        return self.user_profiles.get(user_id)

    def get_approval_scopes(self, user_id: str) -> List[Dict[str, Any]]:
        profile = self.user_profiles.get(user_id, {})
        scopes = profile.get("approval_scopes")
        return scopes if isinstance(scopes, list) else []

    def add_approval_scope(self, user_id: str, scope: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not scope:
            return self.get_approval_scopes(user_id)
        profile = self.user_profiles.get(user_id, {})
        scopes = profile.get("approval_scopes")
        scopes = scopes if isinstance(scopes, list) else []
        if scope not in scopes:
            scopes.append(scope)
        profile["approval_scopes"] = scopes
        if "user_id" not in profile:
            profile["user_id"] = user_id
        profile["updated_at"] = datetime.now().isoformat()
        self.user_profiles[user_id] = profile
        self._save()
        return scopes

    def get_latest_summary(self, user_id: str, session_id: Optional[str] = None) -> Optional[Memory]:
        """Get the most recent summary memory for a user (optionally per session)."""
        summaries = self.recall(user_id, category="summary")
        if session_id:
            summaries = [s for s in summaries if s.session_id == session_id]
        summaries.sort(key=lambda m: m.learned_at, reverse=True)
        return summaries[0] if summaries else None

    def maybe_summarize_session(self, user_id: str, session_id: str, messages: List[Dict[str, Any]]) -> Optional[Memory]:
        """Create a rolling summary every 10 messages to enable long-term recall."""
        if not messages or len(messages) % 10 != 0:
            return None

        latest = self.get_latest_summary(user_id, session_id=session_id)
        if latest and isinstance(latest.data, dict) and latest.data.get("message_count") == len(messages):
            return None

        window = messages[-10:]
        lines = []
        for msg in window:
            role = msg.get("sender", "user")
            content = str(msg.get("content", "")).strip()
            if not content:
                continue
            if self._contains_sensitive(content):
                continue
            lines.append(f"{role}: {content[:160]}")

        summary_text = "\n".join(lines) if lines else "No recent content to summarize."
        data = {
            "message_count": len(messages),
            "summary": summary_text
        }
        return self.learn(user_id, session_id, data, category="summary")
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a specific memory by ID."""
        return self.memories.get(memory_id)
    
    def update_memory(self, memory_id: str, data: Any) -> Optional[Memory]:
        """Update a memory entry."""
        memory = self.get_memory(memory_id)
        if memory:
            memory.data = data
            memory.access()
            self._save()
            return memory
        return None
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        if memory_id in self.memories:
            memory = self.memories[memory_id]
            del self.memories[memory_id]
            
            # Remove from user's memory list
            if memory.user_id in self.user_memories:
                self.user_memories[memory.user_id].remove(memory_id)
            self._save()
            return True
        return False
    
    def get_all_user_memories(self, user_id: str) -> List[Memory]:
        """Get all memories for a user."""
        return self.recall(user_id)
    
    def get_memories_by_category(self, user_id: str, category: str) -> List[Memory]:
        """Get memories for a user by category."""
        return self.recall(user_id, category=category)
    
    def adapt_based_on_memory(self, user_id: str) -> Dict[str, Any]:
        """Get adaptation parameters based on user memory."""
        memories = self.recall(user_id)
        
        # Build adaptation profile from memories
        preferences = {}
        patterns = []
        
        for memory in memories:
            if memory.category == "preference":
                preferences.update(memory.data if isinstance(memory.data, dict) else {})
            elif memory.category == "pattern":
                patterns.append(memory.data)
        
        return {
            "user_id": user_id,
            "preferences": preferences,
            "patterns": patterns,
            "memory_count": len(memories)
        }


# Singleton memory manager
memory_manager = MemoryManager()
