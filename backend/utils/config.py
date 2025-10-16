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
    
    # Evaluation Configuration - Safety & Compliance
    PII_DETECTION_ENABLED: bool = os.getenv("PII_DETECTION_ENABLED", "true").lower() == "true"
    PII_MASKING_MODE = os.getenv("PII_MASKING_MODE", "log_only")  # 'log_only' or 'mask_output'
    SAFETY_SCORE_THRESHOLD = float(os.getenv("SAFETY_SCORE_THRESHOLD", "0.80"))
    
    # Evaluation Configuration - Quality
    BENCHMARK_MODE = os.getenv("BENCHMARK_MODE", "enabled")  # 'enabled' or 'disabled'
    MIN_CITATION_COVERAGE = float(os.getenv("MIN_CITATION_COVERAGE", "0.70"))
    QUALITY_SCORE_THRESHOLD = float(os.getenv("QUALITY_SCORE_THRESHOLD", "0.75"))
    
    # Evaluation Configuration - Monitoring
    METRICS_ENABLED: bool = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    LATENCY_ALERT_THRESHOLD_MS = int(os.getenv("LATENCY_ALERT_THRESHOLD_MS", "5000"))
    COST_ALERT_THRESHOLD_USD = float(os.getenv("COST_ALERT_THRESHOLD_USD", "0.10"))
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.GOOGLE_CLOUD_PROJECT:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")
        if not cls.VERTEX_AI_SEARCH_DATA_STORE_ID:
            raise ValueError("VERTEX_AI_SEARCH_DATA_STORE_ID environment variable is required")


# Validate config on import
Config.validate()

