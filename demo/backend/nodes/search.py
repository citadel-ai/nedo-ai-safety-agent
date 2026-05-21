"""Single-turn search node using the Vertex AI Search Summary API.

Enriches the user query with collected context facts, calls the raw
search tool for full citation metadata, and falls back to the Answer
API when the summary cannot be generated.
"""

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from ..core.state import AgentState
from ..tools.vertex_answer import vertex_answer_tool
from ..tools.vertex_search import vertex_search_raw_tool
from ..utils.citation_extractor import (
    extract_citations_from_answer_response,
    extract_citations_from_raw_response,
)
from ..utils.helpers import get_latest_user_message
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


def search_and_respond(
    state: AgentState,
    config: RunnableConfig | None = None,  # LangGraph will pass this automatically
) -> AgentState:
    """
    Execute Vertex AI Search and return response.

    Following LangGraph patterns:
    - Read from state.messages for latest user query
    - Enhance query with persisted context from collected_facts
    - Return updates to merge into state
    """
    try:
        query_text = get_latest_user_message(state)

        if not query_text:
            return {"error": "No user message found in state"}

        collected_facts = state.get("collected_facts", {})
        visa_type = collected_facts.get("Visa Type")
        location = collected_facts.get("Location")
        nature_of_request = collected_facts.get("Nature of request")

        logger.info(f"Query: {query_text[:100]}...")
        logger.info(f"Collected facts: {collected_facts}")
        if visa_type:
            logger.info(f"Visa type: {visa_type}")
        if location:
            logger.info(f"Location: {location}")
        if nature_of_request:
            logger.info(f"Nature of request: {nature_of_request}")

        query = query_text
        context_parts = []
        for key, value in collected_facts.items():
            if value:  # Only add non-empty facts
                context_parts.append(f"{key}: {value}")

        if context_parts:
            query = f"{query_text} (Context: {', '.join(context_parts)})"
            logger.info(f"Enhanced query: {query}")

        logger.info("Calling Vertex AI Search (with citations)...")
        raw_response = vertex_search_raw_tool.invoke(query)

        summary_text = ""
        if hasattr(raw_response, "summary") and raw_response.summary:
            summary_text = (
                raw_response.summary.summary_with_metadata.summary
            )

        # Detect summary fallback + whether we have references/results
        has_summary = bool(getattr(raw_response, "summary", None))
        has_summary_with_metadata = bool(
            getattr(getattr(raw_response, "summary", None), "summary_with_metadata", None)
        )
        references_count = 0
        try:
            references = getattr(
                getattr(raw_response.summary, "summary_with_metadata", None), "references", None
            )
            if references is not None:
                references_count = len(references)
        except Exception:
            references_count = 0

        results_count = 0
        try:
            results = getattr(raw_response, "results", None)
            if results is not None:
                results_count = len(results)
        except Exception:
            results_count = 0

        summary_lower = (summary_text or "").lower()
        summary_is_fallback = "summary could not be generated" in summary_lower

        logger.info(f"Got response ({len(summary_text)} chars)")

        # If Vertex summary couldn't be generated, fall back to Answer method.
        # This avoids returning the placeholder text without citations even when results exist.
        if summary_is_fallback or (has_summary_with_metadata and references_count == 0):
            try:
                raw_answer_response = vertex_answer_tool.invoke(
                    query,
                    config=config or {},
                    session_id=None,  # single-turn: don't persist sessions
                )

                answer_text = ""
                if hasattr(raw_answer_response, "answer") and raw_answer_response.answer:
                    answer_text = raw_answer_response.answer.answer_text or ""

                if not answer_text:
                    answer_text = (
                        "I couldn't generate an answer. Please try rephrasing your question."
                    )

                citations_data = extract_citations_from_answer_response(raw_answer_response)

                ai_message = AIMessage(content=answer_text)
                return {
                    "messages": [ai_message],
                    "answer": ai_message.content,
                    "citations": citations_data,
                    "error": None,
                }
            except Exception:
                # If fallback fails, continue with original summary path.
                pass

        citations_data = extract_citations_from_raw_response(raw_response)
        logger.info(f"Extracted {len(citations_data)} citations with metadata")

        for cit in citations_data:
            logger.info(f"   [{cit['citation_number']}] {cit['title']}")
            logger.info(f"       URL: {cit['url']}")
            if cit["pages"]:
                logger.info(f"       Pages: {cit['pages']}")

        ai_message = AIMessage(content=summary_text)

        return {
            "messages": [ai_message],
            "answer": ai_message.content,
            "citations": citations_data,
            "error": None,
        }

    except Exception as e:
        error_msg = f"Error calling Vertex AI Search: {str(e)}"
        logger.error(error_msg)
        return {
            "messages": [AIMessage(content=error_msg)],
            "answer": "",
            "error": error_msg,
        }
