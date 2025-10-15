"""
State definitions for the LangGraph agent.
"""

from typing import Annotated, List, Dict, Optional
from langgraph.graph import MessagesState
import operator


def _merge_dicts(existing: Dict, new: Dict) -> Dict:
    """Merge two dicts, with new values overwriting existing ones."""
    return {**existing, **new}


def _replace_list(existing: List, new: List) -> List:
    """Replace existing list with new one (for info cards on follow-ups)."""
    if not new:
        return existing
    return new


class AgentState(MessagesState):
    """
    Agent state extending MessagesState with custom fields.
    
    Following LangGraph best practices:
    - Extends MessagesState for conversation history
    - Uses Annotated with custom reducer for dict merging
    - All fields persist via checkpointing
    """
    # All facts stored as key-value pairs
    # Examples: "Visa Type": "Work", "Location": "Tokyo", "Nature of request": "Healthcare"
    collected_facts: Annotated[Dict[str, str], _merge_dicts] = {}
    
    # Conversation mode (set by UI: 'single' or 'multi')
    conversation_mode: str = "multi"  # Default to multi-turn
    
    # Vertex AI session ID for multi-turn conversations
    vertex_session_id: Optional[str] = None
    
    # Latest response metadata (replaced on each turn, not accumulated)
    answer: str = ""
    citations: Annotated[List[Dict], _replace_list] = []  # Citation dicts with URL, title, pages - replaced on each turn
    error: Optional[str] = None
    
    # Info cards data - replaced on follow-ups (not appended)
    useful_phrases: Annotated[List[Dict], _replace_list] = []  # {"japanese": str, "romaji": str, "english": str}
    useful_places: Annotated[List[Dict], _replace_list] = []  # {"name": str, "address": str, "place_id": str, "maps_url": str}

