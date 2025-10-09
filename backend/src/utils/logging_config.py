"""Centralized logging configuration.

Provides a consistent logging formatter and level across the backend.
This avoids ad-hoc prints and ensures structured, readable logs locally
and in Google Cloud Logging (when enabled elsewhere).
"""

import logging
import os


def initialize_logging(default_level: int | str = logging.INFO) -> logging.Logger:
    """Initialize root logging once with a consistent format.

    - Respects LOG_LEVEL environment variable if present
    - Adds a StreamHandler to the root logger if none are present
    - Leaves Google Cloud Logging setup to the server where applicable
    """

    level: int
    if isinstance(default_level, str):
        default_level = default_level.upper()
    env_level = os.getenv("LOG_LEVEL")
    if env_level:
        try:
            level = getattr(logging, env_level.upper())  # e.g., DEBUG, INFO
        except AttributeError:
            level = logging.INFO
    else:
        level = int(default_level) if isinstance(default_level, int) else logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if not root_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Return a module-level logger for convenience
    return logging.getLogger(__name__)
