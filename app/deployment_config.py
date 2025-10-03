"""
Deployment configuration for Japan Helpdesk system.
Handles graceful initialization in containerized environments.
"""

import logging
import os

logger = logging.getLogger(__name__)


def get_vertex_ai_config() -> dict:
    """Get Vertex AI configuration for deployment."""
    config = {
        "model_name": os.getenv("MODEL_NAME", "gemini-2.5-flash"),
        "location": os.getenv("VERTEX_AI_LOCATION", "asia-northeast1"),
        "temperature": 0.1,
        "max_tokens": 2048,
    }

    # Only add project if it's explicitly set
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if project_id and project_id != "test":
        config["project"] = project_id

    return config


def is_deployment_environment() -> bool:
    """Check if we're running in a deployment environment."""
    return os.getenv("DEPLOYMENT_ENV") == "true" or os.getenv("PORT") is not None


def get_mock_response() -> str:
    """Get a mock response for deployment environments without credentials."""
    return """I'm currently running in deployment mode without proper Google Cloud credentials configured. 
    
To fully activate the Japan Helpdesk system, please:
1. Set up Google Cloud authentication
2. Configure the GOOGLE_CLOUD_PROJECT environment variable
3. Ensure Vertex AI API is enabled

For now, I can provide general information about living in Japan, but I cannot access the full AI-powered assistance."""


def should_use_mock_responses() -> bool:
    """Determine if we should use mock responses instead of real AI."""
    try:
        # Try to check if we have valid credentials
        import google.auth

        credentials, project = google.auth.default()
        return False
    except Exception:
        logger.warning("No valid Google Cloud credentials found, using mock responses")
        return True
