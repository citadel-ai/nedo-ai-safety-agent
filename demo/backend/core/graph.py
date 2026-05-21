"""
LangGraph workflow definition.

Defines the agent's control flow: scope checking, search routing, and
parallel info-agent fan-out.  Context drift detection gates multi-turn
conversations, and the UI-selected mode determines single- vs multi-turn
search.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from ..nodes.check_scope import (
    check_query_scope,
    handle_context_drift,
    handle_out_of_scope,
)
from ..nodes.extract_facts import extract_facts_from_conversation
from ..nodes.find_places import find_useful_places
from ..nodes.generate_phrases import generate_useful_phrases
from ..nodes.search import search_and_respond
from ..nodes.search_answer import search_and_respond_with_answer
from ..utils.logging_config import get_logger
from .state import AgentState

logger = get_logger(__name__)


def _passthrough(state: AgentState) -> AgentState:
    """No-op node used as a routing anchor in the graph."""
    return state


def route_to_search_method(state: AgentState) -> str:
    """Route to the search implementation matching the UI-selected conversation mode.

    Returns:
        ``"search"`` for single-turn (stateless) or ``"search_answer"`` for
        multi-turn (session-aware).
    """
    conversation_mode = state.get("conversation_mode", "multi")

    if conversation_mode == "single":
        logger.info("Single-turn mode — using search() method")
        return "search"

    logger.info("Multi-turn mode — using answer() method with sessions")
    return "search_answer"


def route_to_info_agents(state: AgentState) -> list[Send]:
    """Fan out to all three info agents in parallel via ``Send()``."""
    return [
        Send("extract_facts", state),
        Send("generate_phrases", state),
        Send("find_places", state),
    ]


def create_graph():
    """Build and compile the LangGraph workflow.

    Flow::

        START → check_scope
                 ├─ in_scope   → route_search → search | search_answer
                 │                                └─→ [extract_facts, generate_phrases, find_places] → END
                 ├─ out_of_scope  → END
                 └─ context_drift → END

    Uses an in-memory checkpointer; swap to ``PostgresSaver`` for production.
    """
    workflow = StateGraph(AgentState)

    # Routing anchors (no-op nodes that only serve as conditional-edge sources)
    workflow.add_node("check_scope", _passthrough)
    workflow.add_node("route_search", _passthrough)

    # Functional nodes
    workflow.add_node("out_of_scope", handle_out_of_scope)
    workflow.add_node("context_drift", handle_context_drift)
    workflow.add_node("search", search_and_respond)
    workflow.add_node("search_answer", search_and_respond_with_answer)
    workflow.add_node("extract_facts", extract_facts_from_conversation)
    workflow.add_node("generate_phrases", generate_useful_phrases)
    workflow.add_node("find_places", find_useful_places)

    # Entry point
    workflow.add_edge(START, "check_scope")

    # Scope check → three-way branch
    workflow.add_conditional_edges(
        "check_scope",
        check_query_scope,
        {
            "in_scope": "route_search",
            "out_of_scope": "out_of_scope",
            "context_drift": "context_drift",
        },
    )

    # Search method selector
    workflow.add_conditional_edges(
        "route_search",
        route_to_search_method,
        {"search": "search", "search_answer": "search_answer"},
    )

    # Terminal edges
    workflow.add_edge("out_of_scope", END)
    workflow.add_edge("context_drift", END)

    # Both search paths fan out to info agents, which all converge to END
    workflow.add_conditional_edges("search", route_to_info_agents)
    workflow.add_conditional_edges("search_answer", route_to_info_agents)
    workflow.add_edge("extract_facts", END)
    workflow.add_edge("generate_phrases", END)
    workflow.add_edge("find_places", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


graph = create_graph()
