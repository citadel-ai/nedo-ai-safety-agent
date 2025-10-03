"""
Working Japan Helpdesk LangGraph workflow with fixed state management.
"""

import time
import uuid
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
# MemorySaver removed - using stateless workflow for clean execution

from app.types import JapanHelpdeskState, HIGH_RISK_CATEGORIES
from app.utils.observability import observe, get_langfuse_client, flush_langfuse
from app.utils.error_diagnostics import (
    WorkflowDiagnostics,
    diagnose_intake_failure,
    diagnose_search_failure,
    diagnose_llm_truncation,
    create_detailed_error_response,
    validate_state_integrity,
)
from app.nodes import (
    adversarial_detector_node,
    intake_agent_node,
    query_synthesizer_node,
    scope_checker_node,
    hybrid_search_node,
    legal_checker_node,
    response_synthesizer_node,
    agentic_orchestrator_node,
    evaluator_optimizer_node,
    agentic_search_orchestrator_node,
    multi_step_procedure_agent_node,
)


def create_working_workflow():
    """Create a working Japan Helpdesk workflow with proper routing."""
    workflow = StateGraph(JapanHelpdeskState)

    # Add essential nodes
    workflow.add_node("adversarial_detector", adversarial_detector_node)
    workflow.add_node("intake_agent", intake_agent_node)
    workflow.add_node("query_synthesizer", query_synthesizer_node)
    workflow.add_node("scope_checker", scope_checker_node)

    # Agentic search nodes (NEW!)
    workflow.add_node("agentic_search", agentic_search_orchestrator_node)
    workflow.add_node("multi_step_procedure", multi_step_procedure_agent_node)

    # Original search node (kept as fallback)
    workflow.add_node("hybrid_search", hybrid_search_node)

    workflow.add_node("legal_checker", legal_checker_node)
    workflow.add_node("response_synthesizer", response_synthesizer_node)

    # Other agentic nodes (disabled)
    workflow.add_node("agentic_orchestrator", agentic_orchestrator_node)
    workflow.add_node("evaluator_optimizer", evaluator_optimizer_node)

    # Set entry point
    workflow.set_entry_point("adversarial_detector")

    # Working routing functions
    def route_after_adversarial(
        state: JapanHelpdeskState,
    ) -> Literal["intake_agent", "END"]:
        """Route after adversarial detection - block malicious inputs."""
        adversarial_result = state.get("adversarial_result")
        if adversarial_result and adversarial_result.is_adversarial:
            # Set final response for adversarial inputs
            state["final_response"] = (
                f"I'm sorry, but your request has been flagged as potentially inappropriate: {adversarial_result.reason}. I cannot process this request."
            )
            return "END"
        return "intake_agent"

    def route_after_intake(
        state: JapanHelpdeskState,
    ) -> Literal["query_synthesizer", "END"]:
        """Route after intake.
        - If intake produced follow-up questions, END to await user reply.
        - Otherwise proceed to query synthesis even if intake isn't marked complete.
        """
        intake_session = state.get("intake_session")

        if intake_session:
            # If there are questions to ask, stop and wait for the user
            if getattr(intake_session, "next_questions", None):
                return "END"

            # If no questions (possibly incomplete), proceed to synthesis
            return "query_synthesizer"

        # No intake session available, proceed defensively
        return "query_synthesizer"

    def route_after_scope(
        state: JapanHelpdeskState,
    ) -> Literal["agentic_search", "END"]:
        """Route after scope check - use agentic search if in scope."""
        scope_result = state.get("scope_check_result")
        print(f"🔀 SCOPE ROUTING DEBUG:")
        print(f"   scope_result: {scope_result}")
        print(f"   state keys: {list(state.keys())}")

        if scope_result:
            print(f"   is_in_scope: {scope_result.is_in_scope}")
            print(f"   category: {scope_result.category}")

        if not scope_result or not scope_result.is_in_scope:
            # Set final response for out-of-scope queries
            reason = (
                scope_result.reason
                if scope_result
                else "Please ask about Japanese administrative procedures for foreigners."
            )
            final_msg = f"I'm sorry, but your query is outside my scope. {reason}"
            state["final_response"] = final_msg
            print(f"   TERMINATING: {final_msg}")
            return "END"

        print(f"   PROCEEDING to agentic_search")
        return "agentic_search"

    # Add edges - linear flow
    workflow.add_conditional_edges(
        "adversarial_detector",
        route_after_adversarial,
        {"intake_agent": "intake_agent", "END": END},
    )

    workflow.add_conditional_edges(
        "intake_agent",
        route_after_intake,
        {"query_synthesizer": "query_synthesizer", "END": END},
    )

    # Query synthesizer goes to scope checker
    workflow.add_edge("query_synthesizer", "scope_checker")

    workflow.add_conditional_edges(
        "scope_checker",
        route_after_scope,
        {"agentic_search": "agentic_search", "END": END},
    )

    # New agentic flow:
    # agentic_search -> multi_step_procedure -> legal_checker -> response_synthesizer -> END
    workflow.add_edge("agentic_search", "multi_step_procedure")
    workflow.add_edge("multi_step_procedure", "legal_checker")
    workflow.add_edge("legal_checker", "response_synthesizer")
    workflow.add_edge("response_synthesizer", END)

    # TODO: Re-enable agentic nodes once state management is fixed
    # workflow.add_edge("hybrid_search", "evaluator_optimizer")
    # workflow.add_edge("evaluator_optimizer", "legal_checker")
    # workflow.add_edge("scope_checker", "agentic_orchestrator")
    # workflow.add_edge("agentic_orchestrator", "hybrid_search")

    return workflow


class WorkingJapanHelpdeskAgent:
    """Working Japan Helpdesk agent with fixed state management."""

    def __init__(self):
        """Initialize the working workflow."""
        self.workflow = create_working_workflow()
        # No checkpointer - each request is stateless for clean execution
        self.agent = self.workflow.compile()

    @observe(name="working_japan_helpdesk_query")
    async def process_query(
        self, user_input: str, user_id: str, session_id: str = None
    ) -> Dict[str, Any]:
        """Process a user query through the working workflow."""

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

        # Initialize state with all required fields
        initial_state = JapanHelpdeskState(
            user_input=user_input,
            user_id=user_id,
            session_id=session_id,
            synthesized_search_query=None,
            current_step="start",
            completed_steps=[],
            error_count=0,
            adversarial_result=None,
            intake_session=None,
            scope_check_result=None,
            vector_results=None,
            hybrid_results=None,
            rag_results=None,
            legal_check_result=None,
            agent_plan=None,
            active_todos=[],
            completed_todos=[],
            agent_reasoning=[],
            tool_usage_log=[],
            final_response=None,
            confidence_score=0.0,
            sources=[],
            recommendations=[],
            errors=[],
            fallback_used=False,
            processing_time=0.0,
            tokens_used=0,
            langfuse_trace_id=None,
            _raw_vector_results=None,
            _raw_google_results=None,
            _procedure_breakdown=None,
        )

        # Create diagnostics tracker
        diagnostics = WorkflowDiagnostics()

        try:
            # Validate initial state
            state_issues = validate_state_integrity(initial_state)
            if state_issues:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️ Initial state validation issues: {state_issues}")

            # Execute the workflow (no config needed without checkpointer)
            result_state = await self.agent.ainvoke(initial_state)

            # Validate final state
            final_state_issues = validate_state_integrity(result_state)
            if final_state_issues:
                logger.warning(f"⚠️ Final state validation issues: {final_state_issues}")

            # Calculate total processing time
            total_time = time.time() - start_time

            # Prepare response with COMPREHENSIVE fallback diagnostics
            import logging

            logger = logging.getLogger(__name__)

            final_response = result_state.get("final_response")
            logger.info(
                f"🟢 WORKING AGENT - final_response from workflow: '{final_response}'"
            )

            # Check for LLM truncation issues
            if final_response:
                truncation_issue = diagnose_llm_truncation(final_response)
                if truncation_issue:
                    logger.error(truncation_issue)

            # COMPREHENSIVE fallback logic with diagnostics
            if not final_response or len(final_response.strip()) < 10:
                logger.error(f"🔴 CRITICAL: No valid final_response!")
                logger.error(
                    f"🔴 Completed steps: {result_state.get('completed_steps', [])}"
                )
                logger.error(f"🔴 Errors in state: {result_state.get('errors', [])}")

                # Diagnose what went wrong
                current_step = result_state.get("current_step", "unknown")
                logger.error(f"🔴 Current step: {current_step}")

                # Stage-specific diagnostics
                if "intake" in current_step or not result_state.get("intake_session"):
                    logger.error("🔴 INTAKE FAILURE DIAGNOSIS:")
                    logger.error(diagnose_intake_failure(result_state))
                    final_response = create_detailed_error_response(
                        result_state, "intake"
                    )

                elif "search" in current_step:
                    logger.error("🔴 SEARCH FAILURE DIAGNOSIS:")
                    logger.error(diagnose_search_failure(result_state))
                    final_response = create_detailed_error_response(
                        result_state, "search"
                    )

                else:
                    # Generic but informative error
                    logger.error("🔴 UNKNOWN FAILURE POINT")
                    final_response = create_detailed_error_response(
                        result_state, current_step
                    )

                # Log full state for debugging
                logger.error(f"🔴 FULL STATE DUMP:")
                for key, value in result_state.items():
                    if key not in [
                        "_raw_vector_results",
                        "_raw_google_results",
                    ]:  # Skip large data
                        logger.error(f"   {key}: {str(value)[:200]}")

            logger.info(
                f"🟢 WORKING AGENT - Final response to send: length={len(final_response)}, text='{final_response[:100]}...'"
            )

            # Extract suggested_answers from intake_session if available
            suggested_answers = []
            intake_session = result_state.get("intake_session")
            if intake_session and hasattr(intake_session, "suggested_answers"):
                suggested_answers = intake_session.suggested_answers or []
                logger.info(
                    f"🔵 WORKING AGENT - Extracted {len(suggested_answers)} suggested answers from intake_session"
                )

            response = {
                "response": final_response,
                "confidence_score": result_state.get("confidence_score", 0.0),
                "sources": result_state.get("sources", []),
                "recommendations": result_state.get("recommendations", []),
                "session_id": result_state.get("session_id", session_id),
                "completed_steps": result_state.get("completed_steps", []),
                "errors": result_state.get("errors", []),
                "processing_time": total_time,
                "tokens_used": result_state.get("tokens_used", 0),
                "suggested_answers": suggested_answers,
                "metadata": {
                    "workflow_type": "working_langgraph",
                    "error_count": len(result_state.get("errors", [])),
                    "fallback_used": result_state.get("fallback_used", False),
                    "langfuse_trace_id": None,
                    "diagnostics": diagnostics.get_failure_report()
                    if diagnostics.diagnostics
                    else None,
                },
            }

            flush_langfuse()
            return response

        except Exception as e:
            # Fallback response with error tracking
            total_time = time.time() - start_time
            error_response = {
                "response": f"I apologize, but I encountered a technical error: {str(e)}. Please try again or contact support.",
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
                "suggested_answers": [],
                "metadata": {
                    "workflow_type": "working_langgraph",
                    "error_count": 1,
                    "fallback_used": True,
                    "langfuse_trace_id": None,
                },
            }

            flush_langfuse()
            return error_response


# Create global instance
agent = WorkingJapanHelpdeskAgent()
