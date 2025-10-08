"""
Minimal node implementations without Langfuse decorators to test for the root cause.
"""

from types import AdversarialInputResult, JapanHelpdeskState, ScopeCheckResult


async def minimal_adversarial_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Minimal adversarial detector without decorators."""
    current_count = state.get("step_count", 0)
    print(f"🛡️ ADVERSARIAL NODE CALLED - Current count: {current_count}")

    # Simple mock result
    result = AdversarialInputResult(
        is_adversarial=False,
        threat_type="none",
        confidence=0.9,
        reason="Input is safe and appropriate.",
        sanitized_query=None,
    )

    # Use a simple counter instead of a list
    updated_state = {
        **state,
        "adversarial_result": result,
        "step_count": current_count + 1,
        "completed_steps": state["completed_steps"] + ["adversarial_detection"],
    }

    print(f"🛡️ ADVERSARIAL NODE COMPLETED - Count now: {updated_state['step_count']}")
    return updated_state


async def minimal_scope_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Minimal scope checker without decorators."""
    print(f"🎯 SCOPE NODE CALLED - Current steps: {len(state['completed_steps'])}")

    # Simple mock result
    result = ScopeCheckResult(
        is_in_scope=True, category="visa", reason=None, confidence=0.9
    )

    # Create new state updates instead of mutating existing state
    new_steps = state["completed_steps"] + ["scope_check"]

    updated_state = {
        **state,
        "scope_check_result": result,
        "completed_steps": new_steps,
    }

    print(
        f"🎯 SCOPE NODE COMPLETED - Steps now: {len(updated_state['completed_steps'])}"
    )
    return updated_state


async def minimal_response_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Minimal response synthesizer without decorators."""
    print(f"📝 RESPONSE NODE CALLED - Current steps: {len(state['completed_steps'])}")

    # Create new state updates instead of mutating existing state
    new_steps = state["completed_steps"] + ["response_synthesis"]

    updated_state = {
        **state,
        "final_response": "This is a test response for visa renewal.",
        "confidence_score": 0.8,
        "sources": ["test_source"],
        "recommendations": ["test_recommendation"],
        "completed_steps": new_steps,
    }

    print(
        f"📝 RESPONSE NODE COMPLETED - Steps now: {len(updated_state['completed_steps'])}"
    )
    return updated_state
