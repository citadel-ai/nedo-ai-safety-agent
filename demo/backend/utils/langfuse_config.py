"""Langfuse v3 integration for LLM observability.

Provides a single ``initialize_langfuse()`` entry point (called at server
startup) and exposes the ``CallbackHandler`` and ``@trace`` decorator for
the rest of the application.  All Langfuse functionality degrades gracefully
when the SDK is missing or credentials are absent.
"""

import logging

from .config import Config

logger = logging.getLogger(__name__)

# Global Langfuse client and handler
_langfuse_client = None
_langfuse_handler = None
_langfuse_enabled = False
_langfuse_initialized = False

try:
    from langfuse import Langfuse, get_client, observe
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
        # Initialize Langfuse v3 client and handler.
        #
        # We explicitly construct the client to avoid relying on any specific
        # environment variable naming for the base URL (LANGFUSE_BASE_URL vs LANGFUSE_HOST).
        Langfuse(
            public_key=Config.LANGFUSE_PUBLIC_KEY,
            secret_key=Config.LANGFUSE_SECRET_KEY,
            host=Config.LANGFUSE_HOST,
        )
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


def trace(name: str | None = None):
    """Decorator that wraps a function with Langfuse's ``@observe``.

    When Langfuse is disabled or unavailable the decorator is a no-op.

    Args:
        name: Custom span name shown in the Langfuse dashboard.
              Defaults to the function's ``__name__``.
    """

    def decorator(func):
        if not _langfuse_enabled or not _langfuse_available:
            return func
        return observe(name=name or func.__name__)(func)

    return decorator


# Keep old names as aliases so existing call-sites don't break during migration.
trace_node = trace
trace_llm_call = trace
