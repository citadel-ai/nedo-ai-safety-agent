"""
State definitions for the LangGraph agent.
"""

from typing import Annotated

from langgraph.graph import MessagesState


def _merge_dicts(existing: dict, new: dict) -> dict:
    """Merge two dicts, with new values overwriting existing ones."""
    return {**existing, **new}


def _replace_list(existing: list, new: list) -> list:
    """Replace the list wholesale when the new value is non-empty."""
    if not new:
        return existing
    return new


class AgentState(MessagesState):
    """Conversation state that flows through every node in the graph.

    Extends ``MessagesState`` (which provides ``messages: list[BaseMessage]``)
    with domain-specific fields.  Each field uses an ``Annotated`` reducer so
    LangGraph knows how to merge partial updates returned by nodes.
    """

    collected_facts: Annotated[dict[str, str], _merge_dicts] = {}
    conversation_mode: str = "multi"
    vertex_session_id: str | None = None

    # Per-turn response fields (replaced, not accumulated)
    answer: str = ""
    citations: Annotated[list[dict], _replace_list] = []
    error: str | None = None

    # Info-card payloads (replaced on each turn)
    useful_phrases: Annotated[list[dict], _replace_list] = []
    useful_places: Annotated[list[dict], _replace_list] = []
