"""
User context management service.
"""

from ..core.graph import graph
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


def set_user_context(
    thread_id: str, visa_type: str, location: str, conversation_mode: str = "multi"
) -> dict:
    """
    Set user context for a thread (call this once at start of conversation).

    Following LangGraph best practices:
    - Use thread_id for session isolation
    - Update state directly via graph.update_state()
    - Store all context in collected_facts dict
    - Store conversation mode for routing

    Args:
        thread_id: Unique identifier for this conversation thread
        visa_type: User's visa type
        location: User's location in Japan
        conversation_mode: 'single' or 'multi' - controls search method routing

    Returns:
        Dictionary with confirmation and initial facts
    """
    config = {"configurable": {"thread_id": thread_id}}

    # Prepare initial facts as dict
    facts = {"Visa Type": visa_type, "Location": location}

    logger.info(f"🆕 Setting context for thread {thread_id}")
    logger.info(f"📋 Initial facts: {facts}")
    logger.info(f"🎯 Conversation mode: {conversation_mode}")

    # Initialize or update state with initial facts, empty messages, and conversation mode
    # We need to ensure the state exists before we can update it
    graph.update_state(
        config,
        {
            "collected_facts": facts,
            "messages": [],  # Initialize with empty messages list
            "conversation_mode": conversation_mode,  # Store UI-selected mode
        },
        as_node="__start__",  # Update as if from start node to ensure proper initialization
    )

    logger.info(f"✅ Context set successfully for thread {thread_id}")

    return {
        "status": "success",
        "thread_id": thread_id,
        "collected_facts": facts,
        "conversation_mode": conversation_mode,
    }
