"""Response synthesizer node for LangGraph with Langfuse observability."""

import logging
import time

from src.core.models import JapanHelpdeskState
from src.utils.observability import observe

logger = logging.getLogger(__name__)


@observe(name="response_synthesizer_node")
async def response_synthesizer_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Synthesize final response from all gathered information with citation tracking."""
    start_time = time.time()

    try:
        # Collect all available information
        response_parts = []
        confidence_scores = []
        citations = []  # Track sources for grounding validation

        # Add search results summary with citation tracking (RAG: Vector DB + Google Search)
        if state.get("search_results"):
            response_parts.append(state["search_results"].merged_summary)
            confidence_scores.append(state["search_results"].confidence_score)
            # Track sources for grounding validation
            sources = getattr(state["search_results"], "sources", [])
            if sources:
                citations.extend(sources)
                logger.info(f"📚 Added {len(sources)} sources from search results")

        # Add multi-step procedure recommendations (CRITICAL!)
        if state.get("recommendations") and len(state["recommendations"]) > 0:
            logger.info(
                f"🔧 RESPONSE SYNTH - Including {len(state['recommendations'])} recommendation lines"
            )
            logger.info("🔧 RESPONSE SYNTH - First 5 lines:")
            for line in state["recommendations"][:5]:
                logger.info(f"   {line}")
            response_parts.append("\n" + "\n".join(state["recommendations"]))

        # Add intake context if available
        intake_session = state.get("intake_session")
        if intake_session:
            user_context = getattr(intake_session, "collected_info", {}) or {}
            if user_context.get("location"):
                response_parts.append(
                    f"\n**Location-Specific Note:** Based on your location in {user_context['location']}, please verify local requirements with your municipal office."
                )
            if user_context.get("urgency"):
                response_parts.append(
                    f"\n**Urgency Note:** Given the {user_context['urgency']} nature of your request, consider contacting the relevant office directly."
                )

        # Synthesize final response
        if response_parts:
            final_response = "\n\n".join(response_parts)

            # Add sources section for transparency and grounding
            if citations:
                final_response += "\n\n**Sources:**"
                # Filter out None values and ensure all are strings
                valid_citations = [str(c) for c in citations[:10] if c]  # Top 10, filter None
                unique_sources = list(dict.fromkeys(valid_citations))[:5]  # Top 5 unique, preserving order
                for i, source in enumerate(unique_sources, 1):
                    final_response += f"\n{i}. {source}"
                logger.info(f"📚 Added {len(unique_sources)} sources to response for grounding transparency")

            # Add standard disclaimers
            final_response += "\n\n**Important Disclaimers:**"
            final_response += (
                "\n- This information is for general guidance only and not legal advice"
            )
            final_response += "\n- Always verify current requirements with official government sources"
            final_response += "\n- Consider consulting with qualified professionals for complex situations"
            final_response += (
                "\n- Requirements may vary by location and individual circumstances"
            )

            # Calculate overall confidence
            overall_confidence = (
                sum(confidence_scores) / len(confidence_scores)
                if confidence_scores
                else 0.5
            )

        else:
            final_response = """I apologize, but I couldn't find specific information for your query.

**General Guidance:**
- Visit the relevant government office website (.go.jp domains)
- Contact your local municipal office (市役所) for general procedures
- For visa/immigration matters, contact the Immigration Services Agency
- Consider bringing a Japanese speaker if language is a barrier

**Emergency Contacts:**
- Immigration Services Agency: https://www.moj.go.jp/isa/index.html
- Your local city hall (市役所)

Please try rephrasing your question or provide more specific details about your situation."""
            overall_confidence = 0.0

        # Update state
        state["final_response"] = final_response
        state["confidence_score"] = overall_confidence
        state["completed_steps"].append("response_synthesis")

        processing_time = time.time() - start_time
        state["processing_time"] += processing_time

        # Langfuse v3 automatically captures output via @observe decorator

        return state

    except Exception as e:
        logger.error(f"🔴 RESPONSE SYNTHESIS FAILED: {e}", exc_info=True)
        state["errors"].append(f"Response synthesis failed: {e!s}")
        state["error_count"] += 1

        # Fallback response
        state["final_response"] = (
            "I apologize, but I encountered an error while preparing your response. Please try again or contact support."
        )
        state["confidence_score"] = 0.0

        # Langfuse v3 automatically captures exceptions via @observe decorator
        return state
