"""
Test agent with minimal nodes to isolate the issue.
"""

import uuid
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from app.minimal_nodes import (
    minimal_adversarial_node,
    minimal_response_node,
    minimal_scope_node,
)
from app.types import JapanHelpdeskState


def create_test_workflow():
    """Create a test workflow with minimal nodes."""
    workflow = StateGraph(JapanHelpdeskState)

    # Add minimal nodes
    workflow.add_node("adversarial_detector", minimal_adversarial_node)
    workflow.add_node("scope_checker", minimal_scope_node)
    workflow.add_node("response_synthesizer", minimal_response_node)

    # Set entry point
    workflow.set_entry_point("adversarial_detector")

    # Simple routing with detailed debugging
    def route_after_adversarial(state: JapanHelpdeskState) -> Literal["scope_checker"]:
        print("🔀 ROUTING AFTER ADVERSARIAL CALLED")
        print(f"   Steps: {state['completed_steps']}")
        print(f"   Steps count: {len(state['completed_steps'])}")
        print(f"   Step counter: {state.get('step_count', 'N/A')}")
        return "scope_checker"

    def route_after_scope(state: JapanHelpdeskState) -> Literal["response_synthesizer"]:
        print("🔀 ROUTING AFTER SCOPE CALLED")
        print(f"   Steps: {state['completed_steps']}")
        print(f"   Steps count: {len(state['completed_steps'])}")
        print(f"   Step counter: {state.get('step_count', 'N/A')}")
        return "response_synthesizer"

    # Add edges
    workflow.add_conditional_edges(
        "adversarial_detector",
        route_after_adversarial,
        {"scope_checker": "scope_checker"},
    )

    workflow.add_conditional_edges(
        "scope_checker",
        route_after_scope,
        {"response_synthesizer": "response_synthesizer"},
    )

    workflow.add_edge("response_synthesizer", END)

    return workflow


class TestAgent:
    """Test agent with minimal workflow."""

    def __init__(self):
        """Initialize the test workflow."""
        self.workflow = create_test_workflow()
        # Try without checkpointer to see if that's causing the issue
        self.agent = self.workflow.compile()

    async def process_query(
        self, user_input: str, user_id: str, session_id: str = None
    ) -> dict[str, Any]:
        """Process a query through the test workflow."""

        print("\n🚀 STARTING TEST WORKFLOW")
        print(f"Input: {user_input}")

        session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"

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
            step_count=0,  # Add step counter
        )

        print(f"Initial state steps: {initial_state['completed_steps']}")

        try:
            # Execute the workflow without config since no checkpointer
            print("\n🔄 EXECUTING WORKFLOW...")

            result_state = await self.agent.ainvoke(initial_state)

            print("\n✅ WORKFLOW COMPLETED")
            print(f"Final steps: {result_state['completed_steps']}")
            print(f"Final response: {result_state.get('final_response', 'None')}")

            return {
                "response": result_state.get("final_response", "No response"),
                "confidence_score": result_state.get("confidence_score", 0.0),
                "sources": result_state.get("sources", []),
                "recommendations": result_state.get("recommendations", []),
                "session_id": session_id,
                "completed_steps": result_state.get("completed_steps", []),
                "errors": result_state.get("errors", []),
                "processing_time": 0.0,
                "tokens_used": 0,
                "metadata": {"workflow_type": "test"},
            }

        except Exception as e:
            print(f"❌ WORKFLOW ERROR: {e}")
            import traceback

            traceback.print_exc()

            return {
                "response": f"Error: {e!s}",
                "confidence_score": 0.0,
                "sources": [],
                "recommendations": [],
                "session_id": session_id,
                "completed_steps": ["error"],
                "errors": [str(e)],
                "processing_time": 0.0,
                "tokens_used": 0,
                "metadata": {"workflow_type": "test"},
            }


# Create test instance
test_agent = TestAgent()
