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

"""Observability utilities with Langfuse v3 and optional fallback."""

import os
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Check if Langfuse should be enabled
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"

# Try to import Langfuse v3
langfuse_client = None
if LANGFUSE_ENABLED:
    try:
        from langfuse import Langfuse, observe, get_client

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
def observe_fallback(name: Optional[str] = None):
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


def create_langfuse_trace(name: str, **kwargs) -> Optional[Any]:
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
