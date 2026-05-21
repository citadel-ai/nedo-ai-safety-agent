"""Application configuration loaded from environment variables.

``Config.validate()`` runs at import time to fail fast when required
variables are missing.  Guard the import behind a try/except in test
or tooling code if the full environment is not available.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""

    # Google Cloud Configuration
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    VERTEX_AI_SEARCH_DATA_STORE_ID = os.getenv("VERTEX_AI_SEARCH_DATA_STORE_ID")
    VERTEX_AI_SEARCH_ENGINE_ID = os.getenv("VERTEX_AI_SEARCH_ENGINE_ID")
    GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")  # Optional

    # Langfuse Configuration (Optional - for LLM observability)
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
    # Langfuse v3 docs use LANGFUSE_BASE_URL; keep LANGFUSE_HOST for backwards compatibility.
    LANGFUSE_HOST = os.getenv(
        "LANGFUSE_BASE_URL",
        os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )
    LANGFUSE_ENABLED: bool = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

    # Rate Limiting
    RATE_LIMIT_QUERY = os.getenv("RATE_LIMIT_QUERY", "60/minute")
    RATE_LIMIT_CONTEXT = os.getenv("RATE_LIMIT_CONTEXT", "30/minute")

    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    # API_PORT precedence: PORT (Cloud Run standard) > API_PORT > 8000 (default)
    _port = os.getenv("PORT")
    if _port is not None:
        API_PORT = int(_port)
    else:
        API_PORT = int(os.getenv("API_PORT", "8000"))

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.GOOGLE_CLOUD_PROJECT:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")
        if not cls.VERTEX_AI_SEARCH_DATA_STORE_ID:
            raise ValueError(
                "VERTEX_AI_SEARCH_DATA_STORE_ID environment variable is required"
            )


# Validate config on import
Config.validate()
