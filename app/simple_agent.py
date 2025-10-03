"""
Simplified Japan Helpdesk LangGraph workflow with linear flow to prevent infinite loops.
"""

import time
import uuid
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.nodes import (
    adversarial_detector_node,
    hybrid_search_node,
    legal_checker_node,
    response_synthesizer_node,
    scope_checker_node,
)
from app.types import JapanHelpdeskState
from app.utils.observability import flush_langfuse, observe


def create_simple_workflow():
    """Create a simplified, linear Japan Helpdesk workflow."""
    workflow = StateGraph(JapanHelpdeskState)

    # Add only essential nodes
    workflow.add_node("adversarial_detector", adversarial_detector_node)
    workflow.add_node("scope_checker", scope_checker_node)
    workflow.add_node("hybrid_search", hybrid_search_node)
    workflow.add_node("legal_checker", legal_checker_node)
    workflow.add_node("response_synthesizer", response_synthesizer_node)

    # Set entry point
    workflow.set_entry_point("adversarial_detector")

    # Simple routing functions
    def route_after_adversarial(
        state: JapanHelpdeskState,
    ) -> Literal["scope_checker", "END"]:
        """Route after adversarial detection - block malicious inputs."""
        adversarial_result = state.get("adversarial_result")
        if adversarial_result and adversarial_result.is_adversarial:
            # Set final response for adversarial inputs
            state["final_response"] = (
                f"I'm sorry, but your request has been flagged as potentially inappropriate: {adversarial_result.reason}. I cannot process this request."
            )
            return "END"
        return "scope_checker"

    def route_after_scope(state: JapanHelpdeskState) -> Literal["hybrid_search", "END"]:
        """Route after scope check - terminate if out of scope."""
        scope_result = state.get("scope_check_result")
        print(f"🔀 SCOPE ROUTING: scope_result = {scope_result}")
        if scope_result:
            print(f"🔀 SCOPE ROUTING: is_in_scope = {scope_result.is_in_scope}")
        else:
            print("🔀 SCOPE ROUTING: No scope result found!")

        if not scope_result or not scope_result.is_in_scope:
            # Set final response for out-of-scope queries
            reason = (
                scope_result.reason
                if scope_result
                else "Please ask about Japanese administrative procedures for foreigners."
            )
            state["final_response"] = (
                f"I'm sorry, but your query is outside my scope. {reason}"
            )
            print(f"🔀 SCOPE ROUTING: Terminating - {reason}")
            return "END"
        print("🔀 SCOPE ROUTING: Proceeding to hybrid_search")
        return "hybrid_search"

    # Add edges - completely linear flow
    workflow.add_conditional_edges(
        "adversarial_detector",
        route_after_adversarial,
        {"scope_checker": "scope_checker", "END": END},
    )

    workflow.add_conditional_edges(
        "scope_checker",
        route_after_scope,
        {"hybrid_search": "hybrid_search", "END": END},
    )

    # Linear flow: hybrid_search -> legal_checker -> response_synthesizer -> END
    workflow.add_edge("hybrid_search", "legal_checker")
    workflow.add_edge("legal_checker", "response_synthesizer")
    workflow.add_edge("response_synthesizer", END)

    return workflow


class SimpleJapanHelpdeskAgent:
    """Simplified Japan Helpdesk agent with linear workflow."""

    def __init__(self):
        """Initialize the simplified workflow."""
        self.workflow = create_simple_workflow()
        self.memory = MemorySaver()
        self.agent = self.workflow.compile(checkpointer=self.memory)

    @observe(name="simple_japan_helpdesk_query")
    async def process_query(
        self, user_input: str, user_id: str, session_id: str | None = None
    ) -> dict[str, Any]:
        """Process a user query through the simplified workflow."""

        start_time = time.time()
        session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"

        # Update Langfuse session id on the active trace if available
        try:
            from app.utils.observability import get_langfuse_client, is_langfuse_enabled

            if is_langfuse_enabled():
                lf = get_langfuse_client()
                if lf:
                    lf.update_current_trace(session_id=session_id)
        except Exception:
            pass

        # Initialize state
        initial_state = JapanHelpdeskState(
            user_input=user_input,
            user_id=user_id,
            session_id=session_id,
            conversation_history=[],
            collected_info={},
            completed_steps=[],
            errors=[],
            processing_time=0.0,
            tokens_used=0,
            langfuse_trace_id=None,
        )

        try:
            # Execute the workflow
            config = {"configurable": {"thread_id": session_id}}
            result_state = await self.agent.ainvoke(initial_state, config)

            # Calculate total processing time
            total_time = time.time() - start_time

            # Prepare response
            response = {
                "response": result_state.get(
                    "final_response",
                    "I apologize, but I couldn't process your request.",
                ),
                "confidence_score": result_state.get("confidence_score", 0.0),
                "sources": result_state.get("sources", []),
                "recommendations": result_state.get("recommendations", []),
                "session_id": result_state.get("session_id", session_id),
                "completed_steps": result_state.get("completed_steps", []),
                "errors": result_state.get("errors", []),
                "processing_time": total_time,
                "tokens_used": result_state.get("tokens_used", 0),
                "metadata": {
                    "workflow_type": "simple_langgraph",
                    "error_count": len(result_state.get("errors", [])),
                    "fallback_used": result_state.get("fallback_used", False),
                    "langfuse_trace_id": None,
                },
            }

            flush_langfuse()
            return response

        except Exception as e:
            # Fallback response with error tracking
            total_time = time.time() - start_time
            error_response = {
                "response": f"I apologize, but I encountered a technical error: {e!s}. Please try again or contact support.",
                "confidence_score": 0.0,
                "sources": ["error_fallback"],
                "recommendations": [
                    "Try rephrasing your query",
                    "Contact support if the issue persists",
                ],
                "session_id": session_id,
                "completed_steps": ["error"],
                "errors": [str(e)],
                "processing_time": total_time,
                "tokens_used": 0,
                "metadata": {
                    "workflow_type": "simple_langgraph",
                    "error_count": 1,
                    "fallback_used": True,
                    "langfuse_trace_id": None,
                },
            }

            flush_langfuse()
            return error_response


# Create global instance
simple_agent = SimpleJapanHelpdeskAgent()
