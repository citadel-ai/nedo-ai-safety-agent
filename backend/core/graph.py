"""
LangGraph workflow definition.

Implements routing (scope checking) and parallelization (info agents) patterns.
Enhanced with context drift detection and multi-turn answer support.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import MemorySaver
from typing import List

from .state import AgentState
from ..nodes.check_scope import (
    check_query_scope,
    handle_out_of_scope,
    handle_context_drift,
)
from ..nodes.search import search_and_respond
from ..nodes.search_answer import search_and_respond_with_answer
from ..nodes.extract_facts import extract_facts_from_conversation
from ..nodes.generate_phrases import generate_useful_phrases
from ..nodes.find_places import find_useful_places
from ..utils.config import Config
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


def route_to_search_method(state: AgentState) -> str:
    """
    Route to appropriate search implementation based on UI-selected conversation mode.

    Routing logic:
    - UI selects "Single-turn" → Use search() - fast, stateless
    - UI selects "Multi-turn" → Use answer() - session-aware, context retention

    Returns:
        - "search_answer": Answer method with multi-turn session support
        - "search": Search method for single-turn queries
    """
    # Get the conversation mode set by the UI
    conversation_mode = state.get("conversation_mode", "multi")

    if conversation_mode == "single":
        logger.info("🎯 Single-turn mode selected → using search() method")
        return "search"
    else:
        logger.info("🔄 Multi-turn mode selected → using answer() method with sessions")
        return "search_answer"


def route_to_info_agents(state: AgentState) -> List[Send]:
    """
    Route to all three info agents in parallel.

    Uses Send() for parallel execution per LangGraph parallelization pattern.
    Each agent receives the full state and updates different fields.
    """
    return [
        Send("extract_facts", state),
        Send("generate_phrases", state),
        Send("find_places", state),
    ]


def create_graph():
    """
    Create and compile the LangGraph workflow.

    Enhanced Architecture:
    1. Scope check (with context drift detection)
    2. If out-of-scope: friendly rejection message
    3. If context_drift: warn user to start new conversation
    4. If in-scope: route to search method (old or new based on config)
    5. Search → parallel info agents

    Returns compiled graph with checkpointer.
    """
    # Build the graph
    workflow = StateGraph(AgentState)

    # Add all nodes
    workflow.add_node("check_scope", lambda state: state)  # Dummy node for routing
    workflow.add_node("out_of_scope", handle_out_of_scope)
    workflow.add_node(
        "context_drift", handle_context_drift
    )  # New: context drift handler
    workflow.add_node(
        "route_search", lambda state: state
    )  # Dummy node for search method routing
    workflow.add_node("search", search_and_respond)  # Original search method
    workflow.add_node(
        "search_answer", search_and_respond_with_answer
    )  # New: answer method
    workflow.add_node("extract_facts", extract_facts_from_conversation)
    workflow.add_node("generate_phrases", generate_useful_phrases)
    workflow.add_node("find_places", find_useful_places)

    # Define edges
    workflow.add_edge(START, "check_scope")

    # Conditional routing based on scope check (now with 3 outcomes)
    workflow.add_conditional_edges(
        "check_scope",
        check_query_scope,
        {
            "in_scope": "route_search",  # Route to search method selector
            "out_of_scope": "out_of_scope",
            "context_drift": "context_drift",  # New: route to drift handler
        },
    )

    # Dynamic routing to appropriate search implementation
    workflow.add_conditional_edges(
        "route_search",
        route_to_search_method,
        {
            "search": "search",  # Original search method
            "search_answer": "search_answer",  # New answer method
        },
    )

    # Out-of-scope path goes directly to END
    workflow.add_edge("out_of_scope", END)

    # Context drift path goes directly to END (with warning message)
    workflow.add_edge("context_drift", END)

    # Both search implementations → parallel fan-out to info agents
    workflow.add_conditional_edges("search", route_to_info_agents)
    workflow.add_conditional_edges("search_answer", route_to_info_agents)

    # All info agents converge to END
    workflow.add_edge("extract_facts", END)
    workflow.add_edge("generate_phrases", END)
    workflow.add_edge("find_places", END)

    # Compile with checkpointer (in-memory for development)
    # For production, use PostgresSaver or other persistent checkpointer
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# Create graph instance
graph = create_graph()
