"""
Node execution helpers - Common patterns for node implementation.
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, TypeVar

from src.models import JapanHelpdeskState

logger = logging.getLogger(__name__)

T = TypeVar("T")


@contextmanager
def track_execution(state: JapanHelpdeskState, node_name: str):
    """
    Context manager to track node execution time and update state.
    
    Usage:
        with track_execution(state, "my_node"):
            # Your node logic here
            pass
    """
    start_time = time.time()
    try:
        yield
        state["completed_steps"].append(node_name)
    finally:
        processing_time = time.time() - start_time
        state["processing_time"] = state.get("processing_time", 0) + processing_time


def handle_node_error(
    state: JapanHelpdeskState,
    node_name: str,
    error: Exception,
    default_result: Any = None,
) -> JapanHelpdeskState:
    """
    Standardized error handling for nodes.
    
    Args:
        state: Current state
        node_name: Name of the node for logging
        error: The exception that occurred
        default_result: Optional default value to set in state
        
    Returns:
        Updated state with error logged
    """
    logger.error(f"❌ {node_name.upper()} ERROR: {error}", exc_info=True)
    state["errors"].append(f"{node_name} failed: {str(error)}")
    state["error_count"] = state.get("error_count", 0) + 1
    
    if default_result is not None:
        state[f"{node_name}_result"] = default_result
    
    return state


def safe_execute(
    func: Callable[[JapanHelpdeskState], T],
    state: JapanHelpdeskState,
    node_name: str,
    default_on_error: Any = None,
) -> T | Any:
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        state: Current state
        node_name: Name of the node for logging
        default_on_error: Value to return on error
        
    Returns:
        Result of func or default_on_error
    """
    try:
        return func(state)
    except Exception as e:
        handle_node_error(state, node_name, e)
        return default_on_error


def get_intake_context(state: JapanHelpdeskState) -> dict[str, Any]:
    """
    Extract intake session context from state.
    
    Returns:
        Dictionary with collected context or empty dict
    """
    intake = state.get("intake_session")
    if not intake:
        return {}
    
    return getattr(intake, "collected_info", {}) or {}


def get_main_request(state: JapanHelpdeskState) -> str | None:
    """Get the main user request from intake session."""
    context = get_intake_context(state)
    return context.get("main_request")


def get_user_location(state: JapanHelpdeskState) -> str | None:
    """Get user location from intake session."""
    context = get_intake_context(state)
    location = context.get("location")
    
    if not location:
        intake = state.get("intake_session")
        if intake:
            location = getattr(intake, "user_location", None)
    
    return location


def ensure_state_fields(state: JapanHelpdeskState, fields: dict[str, Any]) -> None:
    """
    Ensure state has required fields with default values.
    
    Args:
        state: State to update
        fields: Dictionary of field_name: default_value
    """
    for field, default in fields.items():
        if field not in state:
            state[field] = default


def log_node_start(node_name: str, user_input: str | None = None) -> None:
    """Log node execution start with consistent formatting."""
    if user_input:
        logger.info(f"🔵 {node_name.upper()} START - Input: '{user_input[:80]}'")
    else:
        logger.info(f"🔵 {node_name.upper()} START")


def log_node_complete(node_name: str, message: str | None = None) -> None:
    """Log node completion with consistent formatting."""
    if message:
        logger.info(f"✅ {node_name.upper()} COMPLETE - {message}")
    else:
        logger.info(f"✅ {node_name.upper()} COMPLETE")

