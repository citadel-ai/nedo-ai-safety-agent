"""
Centralized session management for intake sessions.

This module provides a clean interface for managing user sessions and collected facts,
preparing for future UI sidebar display of collected information.
"""

import uuid
from typing import Any

from src.core.models import IntakeSession


class SessionManager:
    """
    Centralized manager for user sessions.
    
    In production, this should be replaced with a proper database backend
    (Redis for ephemeral sessions, PostgreSQL for persistent storage).
    """
    
    def __init__(self):
        self._sessions: dict[str, IntakeSession] = {}
    
    def get_session(self, session_id: str) -> IntakeSession | None:
        """Get session by ID."""
        return self._sessions.get(session_id)
    
    def create_session(self, user_id: str, session_id: str | None = None) -> IntakeSession:
        """Create a new session."""
        session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        
        session = IntakeSession(
            session_id=session_id,
            user_id=user_id,
            conversation_history=[],
            collected_info={},
            current_step="initial",
            completed_steps=[],
            needs_clarification=[],
            is_complete=False,
        )
        
        self._sessions[session_id] = session
        return session
    
    def get_or_create_session(self, user_id: str, session_id: str | None = None) -> IntakeSession:
        """Get existing session or create new one."""
        if session_id:
            existing = self.get_session(session_id)
            if existing:
                return existing
        
        return self.create_session(user_id, session_id)
    
    def update_session(self, session: IntakeSession) -> None:
        """Update an existing session."""
        self._sessions[session.session_id] = session
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        self._sessions.pop(session_id, None)
    
    def clear_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clear sessions older than max_age_hours.
        
        Note: Current implementation doesn't track timestamps.
        This is a placeholder for future enhancement.
        
        Returns:
            Number of sessions cleared
        """
        # TODO: Add timestamp tracking to IntakeSession
        # For now, just return 0
        return 0
    
    def get_session_count(self) -> int:
        """Get total number of active sessions."""
        return len(self._sessions)


# Global singleton instance
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    return _session_manager

