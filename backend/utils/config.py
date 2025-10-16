"""
Configuration management for the agent.
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
    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    LANGFUSE_ENABLED: bool = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))

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
