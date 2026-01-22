"""
Scope checker node - validates if queries are in-scope for the Japan Procedures Agent.

Enhanced with context awareness to detect conversation drift.
"""

from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel, Field

from ..core.state import AgentState
from ..utils.logging_config import get_logger
from ..utils.model_config import AGENT_MODEL, DEFAULT_TEMPERATURE
from ..utils.langfuse_config import trace_node, trace_llm_call
from ..utils.config import Config
from langchain_google_vertexai import ChatVertexAI

logger = get_logger(__name__)

# Initialize LLM for scope checking with explicit project
llm = ChatVertexAI(
    model=AGENT_MODEL,
    temperature=DEFAULT_TEMPERATURE,
    project=Config.GOOGLE_CLOUD_PROJECT,
)


class ScopeCheckResult(BaseModel):
    """Structured output for scope checking."""

    is_in_scope: bool = Field(
        description="Whether the query is about Japanese official procedures, visas, or living in Japan"
    )
    reason: str = Field(
        description="Brief explanation of why this is in or out of scope"
    )


class ContextCheckResult(BaseModel):
    """Structured output for context continuity checking."""

    continuity: Literal["related", "drift"] = Field(
        description="'related' if the new query is related to previous conversation, 'drift' if it's a completely different topic"
    )
    previous_topic: str = Field(
        description="Brief description of what the previous conversation was about"
    )
    new_topic: str = Field(
        description="Brief description of what the new query is about"
    )
    reason: str = Field(description="Explanation of the continuity assessment")


@trace_node("check_query_scope")
def check_query_scope(
    state: AgentState,
) -> Literal["in_scope", "out_of_scope", "context_drift"]:
    """
    Check if the latest user query is in-scope for the Japan Procedures Agent.
    Enhanced with context awareness to detect conversation drift.

    Returns:
        - "in_scope": Query is in scope and related to conversation (if any)
        - "out_of_scope": Query is not about Japanese procedures
        - "context_drift": Query is in scope but completely unrelated to current conversation

    In-scope topics:
    - Japanese visas and immigration
    - Official procedures in Japan (registration, insurance, etc.)
    - Living in Japan (housing, healthcare, education)
    - Administrative requirements

    Out-of-scope topics:
    - General tourism questions
    - Unrelated topics
    - Personal advice unrelated to procedures
    """
    messages = state["messages"]

    # Get latest user message
    query_text = None
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            query_text = message.content
            break

    if not query_text:
        logger.warning("No user message found for scope check")
        return "in_scope"  # Default to in-scope if no message

    logger.info(f"🔍 Checking scope for query: {query_text[:100]}...")

    # First message - just check basic scope
    if len(messages) <= 1:
        logger.info("📝 First message - checking basic scope only")
        return _check_basic_scope(query_text)

    # Has conversation history - check both scope AND continuity
    logger.info("📜 Conversation history exists - checking scope and continuity")
    return _check_scope_with_context(
        query_text, messages[:-1], state.get("collected_facts", {})
    )


@trace_llm_call("basic_scope_check")
def _check_basic_scope(query: str) -> Literal["in_scope", "out_of_scope"]:
    """
    Check if query is about Japanese procedures (basic scope check).
    Used for first message in conversation.
    """
    structured_llm = llm.with_structured_output(ScopeCheckResult)

    prompt = f"""You are a scope checker for a Japan Procedures Agent that helps foreigners with official procedures in Japan.

Determine if this query is IN-SCOPE or OUT-OF-SCOPE.

IN-SCOPE topics include:
- Visa procedures (application, renewal, change of status)
- Immigration procedures
- Residence registration
- National health insurance
- Tax procedures
- Housing and rental procedures
- Opening bank accounts
- Employment procedures
- Education enrollment
- Government office locations and contacts

OUT-OF-SCOPE topics include:
- General tourism questions (sightseeing, restaurants)
- Entertainment and leisure
- Shopping recommendations
- Language learning (unless about official language requirements)
- Personal advice unrelated to procedures
- Topics unrelated to Japan

User query: "{query}"

Is this query in-scope?"""

    try:
        result = structured_llm.invoke(prompt)

        if result.is_in_scope:
            logger.info(f"✅ Query is IN-SCOPE: {result.reason}")
            return "in_scope"
        else:
            logger.info(f"❌ Query is OUT-OF-SCOPE: {result.reason}")
            return "out_of_scope"

    except Exception as e:
        logger.error(f"Error checking scope: {e}")
        return "in_scope"  # Default to in-scope on error


@trace_llm_call("scope_with_context_check")
def _check_scope_with_context(
    query: str, previous_messages: list, collected_facts: dict
) -> Literal["in_scope", "out_of_scope", "context_drift"]:
    """
    Check scope AND context continuity.

    Returns:
        - "in_scope": In scope and related to previous conversation
        - "out_of_scope": Not about Japanese procedures at all
        - "context_drift": In scope but completely different topic from conversation
    """
    # Build conversation summary (last 3 messages only to avoid token bloat)
    prev_context_messages = []
    for msg in previous_messages[-3:]:
        if isinstance(msg, (HumanMessage, AIMessage)):
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            content = msg.content[:150]  # Truncate for brevity
            prev_context_messages.append(f"{role}: {content}")

    prev_context = "\n".join(prev_context_messages)

    # Format collected facts
    facts_str = (
        ", ".join([f"{k}: {v}" for k, v in collected_facts.items() if v])
        if collected_facts
        else "None"
    )

    # Use structured output for combined scope + continuity check
    structured_llm = llm.with_structured_output(ContextCheckResult)

    prompt = f"""You are analyzing a conversation about Japanese official procedures.

Previous conversation:
{prev_context}

Collected facts about user: {facts_str}

New query: "{query}"

Your task: Determine if the new query is:
1. IN-SCOPE (about Japanese procedures/visas) AND RELATED to the previous conversation? → "related"
2. IN-SCOPE (about Japanese procedures/visas) but COMPLETELY DIFFERENT topic? → "drift"

Examples of DRIFT:
- Previous: work visa renewal → New: healthcare system
- Previous: residence registration → New: opening bank account
- Previous: spouse visa → New: driver's license

Examples of RELATED:
- Previous: work visa → New: required documents for work visa
- Previous: residence registration → New: where is the city hall
- Previous: spouse visa → New: what documents do I need

Assess the continuity:"""

    try:
        result = structured_llm.invoke(prompt)

        if result.continuity == "drift":
            logger.warning("⚠️ CONTEXT DRIFT detected!")
            logger.info(f"   Previous topic: {result.previous_topic}")
            logger.info(f"   New topic: {result.new_topic}")
            logger.info(f"   Reason: {result.reason}")
            return "context_drift"
        else:
            logger.info(f"✅ Query is IN-SCOPE and RELATED: {result.reason}")
            return "in_scope"

    except Exception as e:
        logger.error(f"Error checking context: {e}")
        # On error, do basic scope check
        return _check_basic_scope(query)


@trace_node("handle_out_of_scope")
def handle_out_of_scope(state: AgentState) -> dict:
    """
    Handle out-of-scope queries with a helpful message.

    LangGraph pattern: Return state updates only.
    """
    logger.info("📝 Generating out-of-scope response")

    out_of_scope_message = """I'm specialized in helping with official procedures in Japan, such as:

- 🛂 Visa and immigration procedures
- 📋 Residence registration
- 🏥 Health insurance enrollment
- 🏢 Employment procedures
- 🏠 Housing and rental procedures
- 🏦 Banking and financial procedures
- 📄 Document requirements and applications

Your question seems to be outside my area of expertise. Could you please ask about a specific procedure or requirement related to living in Japan?

For example, you could ask:
- "How do I renew my work visa?"
- "What documents do I need to register at city hall?"
- "How do I enroll in National Health Insurance?"
"""

    ai_message = AIMessage(content=out_of_scope_message)

    return {"messages": [ai_message], "answer": out_of_scope_message, "error": None}


@trace_node("handle_context_drift")
def handle_context_drift(state: AgentState) -> dict:
    """
    Handle context drift - warn user about unrelated query.

    LangGraph pattern: Return state updates only.
    """
    logger.info("⚠️ Generating context drift warning")

    drift_message = """I notice your new question seems unrelated to our previous conversation. 

To give you the most **accurate and focused information** without confusion, I recommend **starting a new conversation** (refresh the page) for this new topic.

This helps ensure:
- ✅ The system stays focused on your specific inquiry
- ✅ Facts collected about your situation remain relevant
- ✅ You get the most accurate answers

**Would you like me to try answering anyway?** (Note: The system might get confused if we switch topics mid-conversation)

Or **refresh the page** to start fresh with your new question."""

    ai_message = AIMessage(content=drift_message)

    return {"messages": [ai_message], "answer": drift_message, "error": None}
