# Copyright 2025 Google LLC

"""Legal advice checker node for LangGraph with Langfuse observability."""

import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_vertexai import ChatVertexAI

from src.models import JapanHelpdeskState, LegalAdviceCheck
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

parser = PydanticOutputParser(pydantic_object=LegalAdviceCheck)


@observe(name="legal_checker_node")
async def legal_checker_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Check for unauthorized legal advice in responses."""
    start_time = time.time()

    try:
        # Get the response content to check
        response_content = ""
        if state.get("hybrid_results"):
            response_content = state["hybrid_results"].merged_summary
        elif state.get("vector_results"):
            response_content = state["vector_results"].merged_summary
        elif state.get("rag_results"):
            response_content = state["rag_results"].summary

        # Langfuse v3 automatically captures context via @observe decorator

        format_instructions = parser.get_format_instructions()
        prompt = f"""
        Check if this response contains unauthorized legal advice.

        {format_instructions}

        Response to check: "{response_content}"
        """

        messages = [
            SystemMessage(content="You are a legal compliance checker."),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)
        result = parser.parse(response.content)

        state["legal_check_result"] = result
        state["completed_steps"].append("legal_check")

        processing_time = time.time() - start_time
        state["processing_time"] += processing_time
        state["tokens_used"] += len(response.content.split())

        # Langfuse v3 automatically captures output via @observe decorator

        return state

    except Exception as e:
        state["errors"].append(f"Legal check failed: {e!s}")
        state["error_count"] += 1

        # Assume compliant if check fails
        state["legal_check_result"] = LegalAdviceCheck(
            contains_legal_advice=False,
            problematic_phrases=[],
            suggested_replacements=[],
            confidence=0.5,
        )

        # Langfuse v3 automatically captures exceptions via @observe decorator
        return state
