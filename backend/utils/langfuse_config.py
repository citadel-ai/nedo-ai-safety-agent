"""
Langfuse v3 integration for LLM observability.

This module handles Langfuse initialization and provides the CallbackHandler
for tracing LangGraph executions and LLM calls.
"""

import logging
from typing import Optional

from .config import Config

logger = logging.getLogger(__name__)

# Global Langfuse client and handler
_langfuse_client = None
_langfuse_handler = None
_langfuse_enabled = False
_langfuse_initialized = False

try:
    from langfuse import get_client, observe
    from langfuse.langchain import CallbackHandler

    _langfuse_available = True
except ImportError:
    _langfuse_available = False
    logger.warning("Langfuse SDK not installed. Run: pip install langfuse>=3.0.0")


def initialize_langfuse():
    """
    Initialize Langfuse v3 client with configuration from environment variables.

    This should be called once at application startup.

    Per Langfuse v3 best practices:
    - Use get_client() to initialize the singleton client
    - Create CallbackHandler without constructor args (v3 change)
    - Set trace attributes via metadata in chain invocation

    Returns:
        Langfuse client instance if successful, None otherwise
    """
    global _langfuse_client, _langfuse_handler, _langfuse_enabled, _langfuse_initialized

    if _langfuse_initialized:
        logger.info("Langfuse already initialized")
        return _langfuse_client

    if not _langfuse_available:
        logger.warning("Langfuse SDK not available. Tracing disabled.")
        _langfuse_enabled = False
        _langfuse_initialized = True
        return None

    if not Config.LANGFUSE_ENABLED:
        logger.info("Langfuse tracing disabled (LANGFUSE_ENABLED=false)")
        _langfuse_enabled = False
        _langfuse_initialized = True
        return None

    if not Config.LANGFUSE_PUBLIC_KEY or not Config.LANGFUSE_SECRET_KEY:
        logger.warning(
            "Langfuse keys not configured. Set LANGFUSE_PUBLIC_KEY and "
            "LANGFUSE_SECRET_KEY to enable tracing."
        )
        _langfuse_enabled = False
        _langfuse_initialized = True
        return None

    try:
        # Configure environment variables for Langfuse SDK
        import os

        os.environ["LANGFUSE_PUBLIC_KEY"] = Config.LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = Config.LANGFUSE_SECRET_KEY
        os.environ["LANGFUSE_HOST"] = Config.LANGFUSE_HOST

        # Initialize Langfuse v3 client and handler
        _langfuse_client = get_client()
        _langfuse_handler = CallbackHandler()

        _langfuse_enabled = True
        _langfuse_initialized = True

        logger.info(f"Langfuse v3 initialized: {Config.LANGFUSE_HOST}")
        return _langfuse_client

    except Exception as e:
        logger.error(f"Failed to initialize Langfuse: {e}")
        _langfuse_enabled = False
        _langfuse_initialized = True
        return None


def is_langfuse_enabled() -> bool:
    """Check if Langfuse tracing is enabled."""
    return _langfuse_enabled


def get_langfuse_handler():
    """
    Get the Langfuse CallbackHandler for LangChain/LangGraph integration.

    This handler should be passed to graph.stream() or graph.invoke() via the config parameter.

    Returns:
        CallbackHandler instance if Langfuse is enabled, None otherwise

    Usage:
        handler = get_langfuse_handler()
        if handler:
            result = graph.invoke(input, config={"callbacks": [handler]})
        else:
            result = graph.invoke(input)
    """
    if not _langfuse_enabled or not _langfuse_handler:
        return None
    return _langfuse_handler


def get_langfuse_client():
    """
    Get the Langfuse client instance.

    Returns:
        Langfuse client if initialized, None otherwise
    """
    return _langfuse_client


def flush_langfuse():
    """Flush all pending traces to Langfuse."""
    if _langfuse_client:
        try:
            _langfuse_client.flush()
        except Exception as e:
            logger.warning(f"Failed to flush Langfuse: {e}")


def trace_node(name: Optional[str] = None):
    """
    Decorator to trace functions with Langfuse @observe decorator.

    Note: For LangGraph nodes, using the CallbackHandler in graph config is preferred.
    This decorator is useful for tracing individual helper functions.

    Args:
        name: Optional custom name for the trace

    Usage:
        @trace_node("my_helper")
        def my_helper_function(data):
            # logic
            return result
    """

    def decorator(func):
        if not _langfuse_enabled or not _langfuse_available:
            # Pass-through if Langfuse is disabled
            return func

        # Apply Langfuse @observe decorator
        trace_name = name or func.__name__
        return observe(name=trace_name)(func)

    return decorator


def trace_llm_call(name: Optional[str] = None):
    """
    Decorator to trace LLM-related functions with Langfuse @observe decorator.

    Args:
        name: Optional custom name for the trace

    Usage:
        @trace_llm_call("vertex_search")
        def call_vertex_search(query: str):
            # LLM call logic
            return response
    """

    def decorator(func):
        if not _langfuse_enabled or not _langfuse_available:
            # Pass-through if Langfuse is disabled
            return func

        # Apply Langfuse @observe decorator
        trace_name = name or func.__name__
        return observe(name=trace_name)(func)

    return decorator
