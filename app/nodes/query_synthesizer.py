"""Query Synthesizer Node - Generates intelligent search queries from conversation context."""

import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI

from app.types import JapanHelpdeskState
from app.utils.observability import observe

# Initialize LLM for query synthesis
llm = ChatVertexAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    max_tokens=256,  # Short queries only
    location="us-central1",
)

QUERY_SYNTHESIS_PROMPT = """
You are a query synthesis agent. Your job is to create effective search queries based on user conversations.

**CRITICAL RULES:**
1. Generate SHORT, focused search queries (3-10 words maximum)
2. Use the ORIGINAL user intent, NOT their latest answer
3. Include collected context (location, visa type, etc.) to make query specific
4. Focus on the ACTION or INFORMATION the user needs
5. Use keywords that will find official government information

**EXAMPLES:**

User Intent: "How do I renew my visa?"
Latest Message: "Student visa, expires in November"
Collected Context: visa_type=Student, timeline=November
→ Query: "student visa renewal procedure Japan November"

User Intent: "Which office handles divorce?"
Latest Message: "I live in Tokyo"
Collected Context: user_location=Tokyo
→ Query: "divorce registration office Tokyo ward office"

User Intent: "How do I open a bank account?"
Latest Message: "Student visa, in Osaka"
Collected Context: visa_type=Student, user_location=Osaka
→ Query: "bank account foreigner student visa Osaka Japan"

User Intent: "Can I work part-time?"
Latest Message: "On a tourist visa"
Collected Context: visa_type=Tourist
→ Query: "tourist visa work restrictions part-time Japan"

**YOUR TASK:**

Original User Query: "{original_query}"
Latest User Message: "{latest_message}"
Collected Context: {collected_context}
Conversation History: {conversation_history}

Generate a SHORT, focused search query (3-10 words) that will find relevant official information.
Return ONLY the search query, nothing else. No explanations, no punctuation at the end.
"""


@observe(name="query_synthesizer_node")
async def query_synthesizer_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Synthesize an intelligent search query from conversation context."""

    import logging

    logger = logging.getLogger(__name__)

    start_time = time.time()

    try:
        # Get intake session for context
        intake_session = state.get("intake_session")

        if not intake_session:
            # No intake session, use original query
            logger.info("🔍 QUERY SYNTHESIS - No intake session, using original query")
            return state

        # Determine original user intent (first user message)
        original_query = state["user_input"]
        if intake_session.conversation_history:
            # Find first user message
            for msg in intake_session.conversation_history:
                if msg.startswith("User:"):
                    original_query = msg.replace("User:", "").strip()
                    break

        # Build collected context string
        collected_context = {}
        if intake_session.visa_type:
            collected_context["visa_type"] = intake_session.visa_type
        if intake_session.user_location:
            collected_context["location"] = intake_session.user_location
        if intake_session.timeline:
            collected_context["timeline"] = intake_session.timeline
        if intake_session.urgency_level:
            collected_context["urgency"] = intake_session.urgency_level

        # Format conversation history (last 5 messages)
        conversation_summary = "\n".join(intake_session.conversation_history[-5:])

        logger.info(
            f"🔍 QUERY SYNTHESIS - Original: '{original_query}', Latest: '{state['user_input']}'"
        )
        logger.info(f"🔍 QUERY SYNTHESIS - Context: {collected_context}")

        # Create synthesis prompt
        prompt = QUERY_SYNTHESIS_PROMPT.format(
            original_query=original_query,
            latest_message=state["user_input"],
            collected_context=collected_context
            if collected_context
            else "No context collected yet",
            conversation_history=conversation_summary,
        )

        messages = [
            SystemMessage(content="You are a query synthesis expert."),
            HumanMessage(content=prompt),
        ]

        # Get synthesized query
        response = await llm.ainvoke(messages)
        synthesized_query = response.content.strip()

        # Clean up the query (remove quotes, extra punctuation)
        synthesized_query = synthesized_query.strip("\"'.,!?")

        logger.info(f"🔍 QUERY SYNTHESIS - Synthesized query: '{synthesized_query}'")

        # Store/overwrite synthesized query in state for search nodes to use
        state["synthesized_search_query"] = synthesized_query

        # Update metadata
        processing_time = time.time() - start_time
        state["processing_time"] += processing_time
        state["tokens_used"] += len(response.content.split())

        return state

    except Exception as e:
        logger.error(f"🔴 QUERY SYNTHESIS ERROR: {e}", exc_info=True)
        state["errors"].append(f"Query synthesis failed: {e!s}")
        # Fall back to original query
        return state
