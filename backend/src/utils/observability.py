"""Observability utilities with Langfuse v3 and optional fallback."""

import logging
import os
from collections.abc import Callable
from typing import Any

from src.core.settings import load_settings

logger = logging.getLogger(__name__)

# Check if Langfuse should be enabled
settings = load_settings()
LANGFUSE_ENABLED = settings.langfuse_enabled

# Langfuse v3 requires keys set in environment variables
if settings.langfuse_public_key:
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
if settings.langfuse_secret_key:
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
if settings.langfuse_secret_key:
    os.environ["LANGFUSE_HOST"] = settings.langfuse_host

# Try to import Langfuse v3
langfuse_client = None
if LANGFUSE_ENABLED:
    try:
        from langfuse import get_client, observe

        # Initialize Langfuse client
        langfuse_client = get_client()
        logger.info("Langfuse v3 initialized successfully")

    except ImportError as e:
        logger.warning(f"Langfuse not available: {e}. Running without observability.")
        LANGFUSE_ENABLED = False
    except Exception as e:
        logger.error(
            f"Failed to initialize Langfuse: {e}. Running without observability."
        )
        LANGFUSE_ENABLED = False


# Fallback decorator when Langfuse is not available
def observe_fallback(name: str | None = None):
    """Fallback decorator when Langfuse is not available or disabled."""

    def decorator(func: Callable) -> Callable:
        return func

    return decorator


# Export the observe decorator (either real or fallback)
if LANGFUSE_ENABLED:
    from langfuse import observe
else:
    observe = observe_fallback


def get_langfuse_client():
    """Get Langfuse client if available, None otherwise."""
    return langfuse_client if LANGFUSE_ENABLED else None


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is enabled and available."""
    return LANGFUSE_ENABLED


def flush_langfuse():
    """Flush Langfuse events if available."""
    if LANGFUSE_ENABLED and langfuse_client:
        try:
            langfuse_client.flush()
        except Exception as e:
            logger.error(f"Failed to flush Langfuse: {e}")


def create_langfuse_trace(name: str, **kwargs) -> Any | None:
    """Create a Langfuse trace if available."""
    if LANGFUSE_ENABLED and langfuse_client:
        try:
            return langfuse_client.trace(name=name, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create Langfuse trace: {e}")
    return None


def score_langfuse_trace(trace_id: str, name: str, value: float, **kwargs):
    """Score a Langfuse trace if available."""
    if LANGFUSE_ENABLED and langfuse_client:
        try:
            langfuse_client.score(trace_id=trace_id, name=name, value=value, **kwargs)
        except Exception as e:
            logger.error(f"Failed to score Langfuse trace: {e}")


# Log the observability status
if LANGFUSE_ENABLED:
    logger.info("🔍 Langfuse v3 observability: ENABLED")
else:
    logger.info("🔍 Langfuse observability: DISABLED (running in fallback mode)")
