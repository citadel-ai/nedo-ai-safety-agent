# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Japan Helpdesk LangGraph workflow with Langfuse v3 observability and guardrails."""

import time
import uuid
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.nodes import (
    adversarial_detector_node,
    hybrid_search_node,
    intake_agent_node,
    legal_checker_node,
    rag_agent_node,
    response_synthesizer_node,
    scope_checker_node,
    vector_rag_node,
)
from app.types import HIGH_RISK_CATEGORIES, JapanHelpdeskState
from app.utils.observability import flush_langfuse, observe


def create_japan_helpdesk_workflow() -> StateGraph:
    """Create the LangGraph workflow for Japan Helpdesk with comprehensive guardrails."""

    # Initialize the state graph
    workflow = StateGraph(JapanHelpdeskState)

    # Add nodes
    workflow.add_node("adversarial_detector", adversarial_detector_node)
    workflow.add_node("intake_agent", intake_agent_node)
    workflow.add_node("scope_checker", scope_checker_node)
    workflow.add_node("vector_rag", vector_rag_node)
    workflow.add_node("hybrid_search", hybrid_search_node)
    workflow.add_node("rag_agent", rag_agent_node)
    workflow.add_node("legal_checker", legal_checker_node)
    workflow.add_node("response_synthesizer", response_synthesizer_node)

    # Set entry point
    workflow.set_entry_point("adversarial_detector")

    # Define conditional routing functions with comprehensive guardrails
    def route_after_adversarial(
        state: JapanHelpdeskState,
    ) -> Literal["intake_agent", "END"]:
        """Route after adversarial detection - HARD STOP for malicious inputs."""
        adversarial_result = state.get("adversarial_result")
        if adversarial_result and adversarial_result.is_adversarial:
            return "END"  # Block adversarial inputs - cannot proceed
        return "intake_agent"

    def route_after_intake(
        state: JapanHelpdeskState,
    ) -> Literal["scope_checker", "END"]:
        """Route after intake - END if more info needed, continue if complete."""
        intake_session = state.get("intake_session")

        # If intake is not complete, END workflow and return question to user
        if intake_session and not intake_session.is_complete:
            return "END"  # User needs to provide more information

        return "scope_checker"  # Intake complete, proceed to scope check

    def route_after_scope(
        state: JapanHelpdeskState,
    ) -> Literal["vector_rag", "hybrid_search", "END"]:
        """Route after scope check based on query type and risk level."""
        scope_result = state.get(
            "scope_check_result"
        )  # Fixed: correct state variable name
        if not scope_result or not scope_result.is_in_scope:
            return "END"  # Out of scope - terminate

        # Route based on query category and risk assessment
        category = scope_result.category
        user_input = state.get("user_input", "").lower()

        # Use hybrid search for current/time-sensitive queries or high-risk categories
        if any(
            keyword in user_input
            for keyword in ["current", "latest", "news", "today", "now"]
        ):
            return "hybrid_search"
        elif category in HIGH_RISK_CATEGORIES:
            return "hybrid_search"
        else:
            return "vector_rag"  # Standard procedures use vector RAG

    def route_after_search(state: JapanHelpdeskState) -> Literal["legal_checker"]:
        """Route after search directly to legal checker - no more branching."""
        return "legal_checker"  # Always go to legal checker after search

    def route_after_legal(
        state: JapanHelpdeskState,
    ) -> Literal["response_synthesizer", "rag_agent"]:
        """Route after legal check - revise if legal advice detected."""
        legal_result = state.get("legal_check_result")
        legal_revision_count = state["completed_steps"].count("legal_check")

        # Limit legal revisions to prevent infinite loops
        if legal_revision_count >= 2:
            return "response_synthesizer"  # Force progression after 2 attempts

        if legal_result and legal_result.contains_legal_advice:
            return "rag_agent"  # Need revision

        return "response_synthesizer"  # Legal check passed

    # Add conditional edges with guardrails
    workflow.add_conditional_edges(
        "adversarial_detector",
        route_after_adversarial,
        {"intake_agent": "intake_agent", "END": END},
    )

    workflow.add_conditional_edges(
        "intake_agent",
        route_after_intake,
        {
            "intake_agent": "intake_agent",  # Loop for more info
            "scope_checker": "scope_checker",
        },
    )

    workflow.add_conditional_edges(
        "scope_checker",
        route_after_scope,
        {"vector_rag": "vector_rag", "hybrid_search": "hybrid_search", "END": END},
    )

    # Simplified: both search nodes go directly to legal checker
    workflow.add_edge("vector_rag", "legal_checker")
    workflow.add_edge("hybrid_search", "legal_checker")

    workflow.add_conditional_edges(
        "legal_checker",
        route_after_legal,
        {"response_synthesizer": "response_synthesizer", "rag_agent": "rag_agent"},
    )

    # Simple edges
    workflow.add_edge("rag_agent", "legal_checker")
    workflow.add_edge("response_synthesizer", END)

    return workflow


class JapanHelpdeskLangGraph:
    """Main class for the LangGraph Japan Helpdesk system with observability."""

    def __init__(self):
        """Initialize the LangGraph workflow with memory and observability."""
        self.workflow = create_japan_helpdesk_workflow()
        self.memory = MemorySaver()
        self.agent = self.workflow.compile(checkpointer=self.memory)

    @observe(name="japan_helpdesk_query")
    async def process_query(
        self, user_input: str, user_id: str, session_id: str | None = None
    ) -> dict[str, Any]:
        """Process a user query through the LangGraph workflow with full observability."""

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
            current_step="adversarial_detection",
            completed_steps=[],
            error_count=0,
            adversarial_result=None,
            intake_session=None,
            scope_check_result=None,
            vector_results=None,
            hybrid_results=None,
            rag_results=None,
            legal_check_result=None,
            final_response=None,
            confidence_score=0.0,
            sources=[],
            recommendations=[],
            errors=[],
            fallback_used=False,
            processing_time=0.0,
            tokens_used=0,
            langfuse_trace_id=None,  # Langfuse v3 handles trace IDs automatically
        )

        try:
            # Execute the workflow
            config = {"configurable": {"thread_id": session_id}}

            # Use ainvoke for simpler execution
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
                    "workflow_type": "langgraph",
                    "error_count": result_state.get("error_count", 0),
                    "fallback_used": result_state.get("fallback_used", False),
                    "langfuse_trace_id": result_state.get("langfuse_trace_id"),
                },
            }

            # Langfuse v3 automatically captures output and usage via @observe decorator
            # Flush events for immediate visibility
            flush_langfuse()

            return response

        except Exception as e:
            # Fallback response with error tracking
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
                "processing_time": time.time() - start_time,
                "tokens_used": 0,
                "metadata": {
                    "workflow_type": "langgraph",
                    "error_count": 1,
                    "fallback_used": True,
                    "langfuse_trace_id": None,  # Langfuse v3 handles trace IDs automatically
                },
            }

            # Langfuse v3 automatically captures exceptions via @observe decorator
            flush_langfuse()

            return error_response


# Create global instance
agent = JapanHelpdeskLangGraph()
