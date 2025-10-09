# Copyright 2025 Google LLC

"""General RAG agent node for LangGraph with Langfuse observability."""

import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_vertexai import ChatVertexAI

from src.models import JapanHelpdeskState, LegalResponse
from src.settings import load_settings
from src.utils.observability import observe

# Initialize settings
settings = load_settings()

llm = ChatVertexAI(
    model=settings.agent_model,
    temperature=settings.agent_temperature,
    max_tokens=settings.agent_max_tokens,
    location=settings.vertex_ai_location,
)
parser = PydanticOutputParser(pydantic_object=LegalResponse)


@observe(name="rag_agent_node")
async def rag_agent_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """General RAG agent for fallback responses."""
    start_time = time.time()

    try:
        query = state["user_input"]
        format_instructions = parser.get_format_instructions()

        # Langfuse v3 automatically captures context via @observe decorator

        prompt = f"""
        Provide general guidance for this Japan administrative query.
        Focus on official procedures and requirements.

        {format_instructions}

        Query: "{query}"
        """

        messages = [
            SystemMessage(
                content="You are a general Japan administrative guidance agent."
            ),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)
        result = parser.parse(response.content)

        state["rag_results"] = result
        state["completed_steps"].append("rag_agent")
        state["sources"].extend(result.sources)

        processing_time = time.time() - start_time
        state["processing_time"] += processing_time
        state["tokens_used"] += len(response.content.split())

        # Langfuse v3 automatically captures output via @observe decorator

        return state

    except Exception as e:
        state["errors"].append(f"RAG agent failed: {e!s}")
        state["error_count"] += 1
        # Langfuse v3 automatically captures exceptions via @observe decorator
        return state
