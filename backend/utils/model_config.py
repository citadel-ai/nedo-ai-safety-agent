"""
Centralized model configuration for the application.
"""

# Model used for agent nodes (fact extraction, phrase generation, place finding, scope checking)
AGENT_MODEL = "gemini-2.5-flash"

# Model used for Vertex AI Search responses
SEARCH_MODEL = "gemini-2.5-pro"

# Temperature settings
DEFAULT_TEMPERATURE = 0
CREATIVE_TEMPERATURE = 0.7

