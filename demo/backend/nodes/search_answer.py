"""Multi-turn search node using the Vertex AI Answer API with session support.

Maintains a Vertex AI session across conversation turns so follow-up
questions automatically have access to prior context.
"""

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from ..core.state import AgentState
from ..tools.vertex_answer import vertex_answer_tool
from ..utils.citation_extractor import extract_citations_from_answer_response
from ..utils.helpers import get_latest_user_message
from ..utils.langfuse_config import trace_node
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


@trace_node("search_and_respond_with_answer")
def search_and_respond_with_answer(
    state: AgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """
    Execute Vertex AI Search using answer method with session support.

    LangGraph patterns:
    - Accepts RunnableConfig for thread_id access
    - Returns dict of updates (merged by LangGraph)
    - Keeps logic simple and focused

    The answer method automatically handles multi-turn conversation context
    via sessions, which are persisted in the state.
    """
    try:
        query_text = get_latest_user_message(state)

        if not query_text:
            return {"error": "No user message found in state"}

        existing_session_id = state.get("vertex_session_id")
        collected_facts = state.get("collected_facts", {})
        query = query_text

        if collected_facts:
            context_parts = [f"{k}: {v}" for k, v in collected_facts.items() if v]
            if context_parts:
                query = f"{query_text} (Context: {', '.join(context_parts)})"
                logger.info("Enhanced query with context")

        logger.info(f"Answer query: {query[:100]}...")
        logger.info(f"Collected facts: {collected_facts}")
        if existing_session_id:
            logger.info(f"Using existing session: ...{existing_session_id[-8:]}")

        raw_response = vertex_answer_tool.invoke(
            query,
            config=config,
            session_id=existing_session_id,
        )

        answer_text = ""
        if hasattr(raw_response, "answer") and raw_response.answer:
            answer_text = raw_response.answer.answer_text

        if not answer_text:
            logger.warning("No answer text in response")
            answer_text = (
                "I couldn't generate an answer. Please try rephrasing your question."
            )

        logger.info(f"Got answer ({len(answer_text)} chars)")

        new_session_id = None
        if hasattr(raw_response, "session") and raw_response.session:
            session_name = raw_response.session.name
            if "/sessions/" in session_name:
                new_session_id = session_name.split("/sessions/")[-1]
                if not existing_session_id:
                    logger.info(f"Created new session: {new_session_id}")
                logger.info("Storing session ID for future turns")

        citations = extract_citations_from_answer_response(raw_response)
        logger.info(f"Extracted {len(citations)} citations")

        for cit in citations:
            logger.info(f"   [{cit['citation_number']}] {cit['title']}")
            if cit.get("url"):
                logger.info(f"       URL: {cit['url']}")

        state_updates = {
            "messages": [AIMessage(content=answer_text)],
            "answer": answer_text,
            "citations": citations,
            "error": None,
        }

        # Best-effort: set trace-level output to the final answer so it shows up as the
        # "main generated content" in Langfuse trace output.
        try:
            from langfuse import get_client

            lf = get_client()
            lf.update_current_trace(
                output={
                    "answer": answer_text,
                    "citations": citations,
                }
            )
        except Exception:
            # Don't let observability break the agent.
            pass

        if new_session_id:
            state_updates["vertex_session_id"] = new_session_id

        return state_updates

    except Exception as e:
        error_msg = f"Error calling Vertex AI Answer: {str(e)}"
        logger.error(error_msg)
        return {
            "messages": [AIMessage(content=error_msg)],
            "answer": "",
            "error": error_msg,
        }
