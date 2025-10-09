"""
LLM Factory - Centralized LLM creation with common configurations.
"""

from langchain_google_vertexai import ChatVertexAI

from src.core.settings import load_settings

# Global settings instance
_settings = load_settings()


def create_llm(
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> ChatVertexAI:
    """
    Create a ChatVertexAI instance with sensible defaults.
    
    Args:
        temperature: Override default temperature (0.3)
        max_tokens: Override default max_tokens (2048)
        model: Override default model
    
    Returns:
        Configured ChatVertexAI instance
    """
    return ChatVertexAI(
        model=model or _settings.agent_model,
        temperature=temperature if temperature is not None else _settings.agent_temperature,
        max_tokens=max_tokens or _settings.agent_max_tokens,
        location=_settings.vertex_ai_location,
    )


def create_query_llm() -> ChatVertexAI:
    """Create LLM optimized for short query generation."""
    return create_llm(temperature=0.3, max_tokens=256)


def create_planning_llm() -> ChatVertexAI:
    """Create LLM optimized for creative planning."""
    return create_llm(temperature=0.7)


def create_procedure_llm() -> ChatVertexAI:
    """Create LLM optimized for detailed multi-step procedures."""
    return create_llm(max_tokens=4096)


def create_evaluation_llm() -> ChatVertexAI:
    """Create LLM optimized for evaluation tasks."""
    return create_llm(temperature=0.1, max_tokens=1024)


def create_optimization_llm() -> ChatVertexAI:
    """Create LLM optimized for response optimization."""
    return create_llm(temperature=0.3, max_tokens=2048)

