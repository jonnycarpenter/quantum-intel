"""
Session Store
=============

Basic in-memory session store to maintain conversation history
across independent API calls, particularly for streaming.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class ChalkSession:
    def __init__(self, session_id: str, surface: str):
        self.id = session_id
        self.surface = surface
        self.messages = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, ChalkSession] = {}
        self._lock = asyncio.Lock()
        self.ttl_hours = 4
        
    async def get(self, session_id: str) -> Optional[ChalkSession]:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_activity = datetime.now()
            return session
            
    async def get_or_create(self, session_id: str, surface: str) -> ChalkSession:
        async with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = ChalkSession(session_id, surface)
            else:
                self._sessions[session_id].last_activity = datetime.now()
            return self._sessions[session_id]
            
    async def save(self, session: ChalkSession) -> None:
        async with self._lock:
            self._sessions[session.id] = session
            session.last_activity = datetime.now()

    async def cleanup_expired(self) -> int:
        async with self._lock:
            now = datetime.now()
            expired = [
                sid for sid, sess in self._sessions.items()
                if now - sess.last_activity > timedelta(hours=self.ttl_hours)
            ]
            for sid in expired:
                del self._sessions[sid]
            return len(expired)

# Singleton instance
store = SessionStore()

def get_session_store() -> SessionStore:
    return store
