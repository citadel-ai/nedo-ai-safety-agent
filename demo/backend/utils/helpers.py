"""Shared helper utilities used across agent nodes."""

from langchain_core.messages import HumanMessage

from ..core.state import AgentState


def get_latest_user_message(state: AgentState) -> str | None:
    """Return the content of the most recent HumanMessage, or None if absent."""
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return message.content
    return None
