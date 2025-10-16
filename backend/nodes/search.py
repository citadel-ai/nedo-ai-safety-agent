"""
Search node for the LangGraph agent with citation extraction.
"""

from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
import re

from ..core.state import AgentState
from ..tools.vertex_search import vertex_search_tool, vertex_search_raw_tool
from ..utils.citation_extractor import (
    extract_citations_from_raw_response,
    extract_inline_citation_numbers,
)
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


def search_and_respond(state: AgentState) -> AgentState:
    """
    Execute Vertex AI Search and return response.

    Following LangGraph patterns:
    - Read from state.messages for latest user query
    - Enhance query with persisted context from collected_facts
    - Return updates to merge into state
    """
    try:
        # Get latest user message
        query_text = None
        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                query_text = message.content
                break

        if not query_text:
            return {"error": "No user message found in state"}

        # Extract context from collected_facts (dict)
        collected_facts = state.get("collected_facts", {})
        visa_type = collected_facts.get("Visa Type")
        location = collected_facts.get("Location")
        nature_of_request = collected_facts.get("Nature of request")

        # Log debug info (unobtrusive)
        logger.info(f"🔍 Query: {query_text[:100]}...")
        logger.info(f"📋 Collected Facts: {collected_facts}")
        if visa_type:
            logger.info(f"🎫 Visa Type: {visa_type}")
        if location:
            logger.info(f"📍 Location: {location}")
        if nature_of_request:
            logger.info(f"🏥 Nature of request: {nature_of_request}")

        # Enhance query with context
        query = query_text
        context_parts = []
        for key, value in collected_facts.items():
            if value:  # Only add non-empty facts
                context_parts.append(f"{key}: {value}")

        if context_parts:
            query = f"{query_text} (Context: {', '.join(context_parts)})"
            logger.info(f"🔧 Enhanced Query: {query}")

        # Call Vertex AI Search (get raw response for citations)
        logger.info("🌐 Calling Vertex AI Search (with citations)...")
        raw_response = vertex_search_raw_tool.invoke(query)

        # Extract summary text
        summary_text = ""
        if hasattr(raw_response, "summary") and raw_response.summary:
            summary_text = (
                raw_response.summary.summary_with_metadata.summary
            )  # summary_text will have [1] inline citations

        logger.info(f"✅ Got response ({len(summary_text)} chars)")

        # Extract structured citations with URLs
        citations_data = extract_citations_from_raw_response(raw_response)
        logger.info(f"📚 Extracted {len(citations_data)} citations with metadata")

        # Log citation details
        for cit in citations_data:
            logger.info(f"   [{cit['citation_number']}] {cit['title']}")
            logger.info(f"       URL: {cit['url']}")
            if cit["pages"]:
                logger.info(f"       Pages: {cit['pages']}")

        # Create AI response message
        ai_message = AIMessage(content=summary_text)

        # Return state updates (will be merged via checkpointing)
        return {
            "messages": [ai_message],  # Appended to existing messages
            "answer": ai_message.content,
            "citations": citations_data,  # List of dicts with URL, title, pages
            "error": None,
        }

    except Exception as e:
        error_msg = f"Error calling Vertex AI Search: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "messages": [AIMessage(content=error_msg)],
            "answer": "",
            "error": error_msg,
        }
