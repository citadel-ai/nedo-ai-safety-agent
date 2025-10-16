"""
Query processing service.
"""

from typing import Dict, List

from langchain_core.messages import HumanMessage

from ..core.graph import graph
from ..utils.langfuse_config import get_langfuse_handler
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


def query_agent(question: str, thread_id: str, conversation_mode: str = None) -> dict:
    """
    Query the agent with a question.

    Following LangGraph best practices:
    - Use thread_id for state persistence
    - State automatically loaded from checkpoint
    - Messages and context accumulate across calls
    - Langfuse CallbackHandler for tracing (if enabled)
    - Session tracking using thread_id as sessionId

    Args:
        question: User's question
        thread_id: Thread identifier (must match set_user_context call)
        conversation_mode: Optional - allows switching mode mid-conversation ('single' or 'multi')

    Returns:
        Dictionary with answer, citations, collected facts, and metadata
    """
    # Build config with thread_id
    config = {"configurable": {"thread_id": thread_id}}

    # Add Langfuse CallbackHandler with session tracking
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        # Extract user context for metadata
        try:
            snapshot = graph.get_state(config)
            collected_facts = (
                snapshot.values.get("collected_facts", {})
                if snapshot and snapshot.values
                else {}
            )
            visa_type = collected_facts.get("Visa Type", "unknown")
            location = collected_facts.get("Location", "unknown")
        except Exception as e:
            visa_type = location = "unknown"
            logger.error(f"❌ Error getting state: {str(e)}", exc_info=True)

        # Build dynamic tags
        tags = ["japan-procedures", "conversation"]
        if visa_type != "unknown":
            tags.append(f"visa-{visa_type.lower().replace(' ', '-')}")
        if location != "unknown":
            tags.append(f"location-{location.lower().replace(' ', '-')}")

        # Configure tracing with session tracking, tags, and metadata
        config["callbacks"] = [langfuse_handler]
        config["metadata"] = {
            "langfuse_session_id": thread_id,
            "langfuse_tags": tags,
            "visa_type": visa_type,
            "location": location,
            "query_type": "conversation",
        }

    logger.info(f"💬 Query for thread {thread_id}: {question}")

    # Prepare input with message and optional conversation_mode update
    input_data = {"messages": [HumanMessage(content=question)]}

    # If conversation_mode is provided, update it (allows switching mid-conversation)
    if conversation_mode:
        input_data["conversation_mode"] = conversation_mode
        logger.info(f"🔄 Switching conversation mode to: {conversation_mode}")

    # Invoke graph with new message
    # State is automatically loaded from checkpoint and merged with input
    result = graph.invoke(input_data, config)

    # Extract context from collected_facts (now a dict)
    collected_facts: Dict[str, str] = result.get("collected_facts", {})
    visa_type = collected_facts.get("Visa Type")
    location = collected_facts.get("Location")

    return {
        "query": question,
        "answer": result.get("answer", ""),
        "citations": result.get("citations", []),
        "error": result.get("error"),
        "visa_type": visa_type,  # For backward compatibility with frontend
        "location": location,  # For backward compatibility with frontend
        "collected_facts": collected_facts,  # Send as dict
        "useful_phrases": result.get("useful_phrases", []),
        "useful_places": result.get("useful_places", []),
    }


def get_thread_state(thread_id: str) -> dict:
    """
    Get current state of a conversation thread.

    Args:
        thread_id: Thread identifier

    Returns:
        Current state snapshot
    """
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    if not snapshot or not snapshot.values:
        return {"error": "Thread not found"}

    state = snapshot.values
    collected_facts = state.get("collected_facts", {})

    return {
        "visa_type": collected_facts.get("Visa Type"),
        "location": collected_facts.get("Location"),
        "collected_facts": collected_facts,  # Return as dict
        "message_count": len(state.get("messages", [])),
        "last_answer": state.get("answer", ""),
        "citations": state.get("citations", []),
    }


def get_thread_history(thread_id: str) -> List[dict]:
    """
    Get full checkpoint history for a thread.

    Args:
        thread_id: Thread identifier

    Returns:
        List of checkpoint snapshots (newest first)
    """
    config = {"configurable": {"thread_id": thread_id}}
    history = []

    for state in graph.get_state_history(config):
        history.append(
            {
                "checkpoint_id": state.config["configurable"]["checkpoint_id"],
                "timestamp": state.metadata.get("ts"),
                "message_count": len(state.values.get("messages", [])),
                "collected_facts_count": len(state.values.get("collected_facts", {})),
                "has_error": bool(state.values.get("error")),
            }
        )

    return history


def remove_collected_fact(thread_id: str, fact_key: str) -> dict:
    """
    Remove a specific fact from collected_facts.

    Args:
        thread_id: Thread identifier
        fact_key: Key of the fact to remove (e.g., "Visa Type")

    Returns:
        Updated collected_facts dict
    """
    config = {"configurable": {"thread_id": thread_id}}

    try:
        snapshot = graph.get_state(config)
        logger.info(f"📊 Snapshot exists: {snapshot is not None}")

        if not snapshot or not snapshot.values:
            logger.error(f"❌ Thread {thread_id} not found in checkpoint store")
            return {
                "error": f"Thread '{thread_id}' not found. Please start a new conversation."
            }

        collected_facts = snapshot.values.get("collected_facts", {})
        logger.info(f"📋 Current facts in state: {collected_facts}")
        logger.info(f"🔑 Attempting to remove fact key: '{fact_key}'")
        logger.info(f"🔑 Available keys: {list(collected_facts.keys())}")

        if fact_key not in collected_facts:
            logger.warning(
                f"⚠️  Fact key '{fact_key}' not found in {list(collected_facts.keys())}"
            )
            return {
                "error": f"Fact '{fact_key}' not found. Available facts: {list(collected_facts.keys())}"
            }

        # Remove the fact by creating a new dict without it
        updated_facts = {k: v for k, v in collected_facts.items() if k != fact_key}
        logger.info(f"📝 Updated facts: {updated_facts}")

        # Update state with the new facts dict
        graph.update_state(
            config,
            {"collected_facts": updated_facts},
            as_node="__start__",  # Update as if from start node
        )

        logger.info(
            f"✅ Successfully removed fact '{fact_key}' from thread {thread_id}"
        )

        return {
            "status": "removed",
            "removed_key": fact_key,
            "collected_facts": updated_facts,
        }
    except Exception as e:
        logger.error(f"❌ Exception in remove_collected_fact: {str(e)}", exc_info=True)
        return {"error": f"Failed to remove fact: {str(e)}"}
