# Copyright 2025 Google LLC

"""Scope checker node for LangGraph with Langfuse v3 observability."""

import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from src.core.models import SUPPORTED_CATEGORIES, JapanHelpdeskState, ScopeCheckResult
from src.utils.llm_factory import create_llm
from src.utils.node_helpers import (
    get_main_request,
    get_user_location,
    handle_node_error,
    track_execution,
)
from src.utils.observability import observe

# Initialize LLM and parser
llm = create_llm()
parser = PydanticOutputParser(pydantic_object=ScopeCheckResult)

SCOPE_CHECK_PROMPT = """
Determine if this user request is within scope for a Japan Helpdesk system.
Use the overall conversation context, not only the latest short reply.

IN SCOPE: visa, immigration, housing, tax, employment, healthcare, banking,
education, marriage, driving, residence card, pension, insurance, business
registration, general procedures.

OUT OF SCOPE: illegal activities (e.g., tax evasion, forged documents,
bribery), specific legal advice, medical advice, investment advice, non-Japan
related queries.

IMPORTANT:
- If the latest user message is a short answer to a follow-up question (e.g.,
  just a location like "Tokyo"), treat it as context and evaluate scope based
  on the user's main request and collected context.
- Prefer the synthesized or main user intent over the latest short message
  when determining scope.
- If the intent appears to be illegal or to bypass laws (e.g., "how to avoid
  taxes", "how to evade taxes", "how to fake documents"), classify as OUT OF
  SCOPE with a clear reason.

EXAMPLES:
- "How do I avoid taxes?" → OUT OF SCOPE (illegal intent)
- "How to evade taxes in Japan?" → OUT OF SCOPE (illegal intent)
- "What documents do I need for address registration?" → IN SCOPE
  (general procedures)
- Latest: "Tokyo" with earlier intent "student visa renewal" → IN SCOPE
  (treat "Tokyo" as context)

{format_instructions}

Context: {context}
Evaluated Query: "{query}"
"""

# Illegal intent patterns
ILLEGAL_PHRASES = [
    "tax evasion",
    "bypass the law",
    "cheat the system",
    "forged",
    "fake",
    "bribe",
    "illegally",
]

ILLEGAL_PATTERNS = [
    r"\bavoid(ing)?\s+tax(es)?\b",
    r"\bevad(e|ing|ed)\s+tax(es)?\b",
    r"\bdodg(e|ing|ed)\s+tax(es)?\b",
    r"\bcheat(ing)?\s+tax(es)?\b",
]


def _classify_category(text: str) -> str:
    """Classify text into a supported category using keyword matching."""
    text_lower = (text or "").lower()

    category_keywords = {
        "visa": [
            "visa",
            "immigration",
            "residence card",
            "status of residence",
        ],
        "housing": ["housing", "rental", "apartment", "lease"],
        "tax": ["tax", "taxes", "withholding", "my number"],
        "employment": ["work", "employment", "job", "part-time", "baito"],
        "healthcare": ["health", "insurance", "clinic", "hospital", "nhis"],
        "banking": ["bank", "account", "atm", "transfer"],
        "education": ["school", "education", "university", "enrollment"],
        "marriage": ["marriage", "divorce", "koseki", "registration"],
        "driving_license": ["license", "driving", "jaf", "convert"],
        "pension": ["pension", "nenkin"],
        "insurance": ["insurance", "national health", "kokumin"],
        "business_registration": [
            "business",
            "company",
            "registration",
            "incorporate",
        ],
    }

    for category, keywords in category_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return category

    return "general_procedures"


def _is_short_context_reply(user_input: str) -> bool:
    """Check if input is a short contextual reply."""
    return (
        len(user_input.split()) <= 3 and user_input.lower() not in {"yes", "no"}
    )


def _check_illegal_intent(text: str) -> bool:
    """Check if text contains illegal intent patterns."""
    text_lower = text.lower()

    # Check phrase matches
    if any(phrase in text_lower for phrase in ILLEGAL_PHRASES):
        return True

    # Check regex patterns
    return any(re.search(pattern, text_lower) for pattern in ILLEGAL_PATTERNS)


def _get_evaluated_query(state: JapanHelpdeskState) -> tuple[str, dict]:
    """Extract evaluated query and context from state."""
    intake = state.get("intake_session")
    main_request = get_main_request(state)
    location = get_user_location(state)
    visa_type = getattr(intake, "visa_type", None) if intake else None
    latest = state["user_input"]
    synthesized = state.get("synthesized_search_query")
    summary = getattr(intake, "conversation_summary", "") if intake else ""

    # Build evaluated query
    evaluated_query = synthesized or main_request or latest

    # If latest is short context, try to extract location
    if main_request and _is_short_context_reply(latest) and not location:
        location = latest

    context = {
        "main_request": main_request or evaluated_query,
        "location": location,
        "visa_type": visa_type,
        "latest_user_message": latest,
        "conversation_summary": summary,
        "synthesized_search_query": synthesized,
    }

    return evaluated_query, context


@observe(name="scope_checker_node")
async def scope_checker_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Check if query is within supported scope."""

    try:
        with track_execution(state, "scope_check"):
            evaluated_query, context = _get_evaluated_query(state)
            latest = state["user_input"]
            main_request = get_main_request(state)
            synthesized = state.get("synthesized_search_query")

            # Fast path: Short context reply with known main intent
            if (synthesized or main_request) and _is_short_context_reply(latest):
                category = _classify_category(synthesized or main_request)
                if category in SUPPORTED_CATEGORIES:
                    state["scope_check_result"] = ScopeCheckResult(
                        is_in_scope=True, category=category, reason=None, confidence=0.9
                    )
                    return state

            # Check for illegal intent
            combined_text = f"{evaluated_query} {latest}"
            if _check_illegal_intent(combined_text):
                state["scope_check_result"] = ScopeCheckResult(
                    is_in_scope=False,
                    category=None,
                    reason=(
                        "Request appears to seek illegal activity "
                        "(e.g., tax evasion), which is out of scope."
                    ),
                    confidence=0.95,
                )
                return state

            # LLM-based scope check
            format_instructions = parser.get_format_instructions()
            prompt = SCOPE_CHECK_PROMPT.format(
                query=evaluated_query,
                context=context,
                format_instructions=format_instructions,
            )

            messages = [
                SystemMessage(content="You are a scope checking system."),
                HumanMessage(content=prompt),
            ]

            response = await llm.ainvoke(messages)
            result = parser.parse(response.content)

            state["scope_check_result"] = result
            state["tokens_used"] = state.get("tokens_used", 0) + len(
                response.content.split()
            )

            if not result.is_in_scope:
                state["final_response"] = (
                    f"I'm sorry, but your query is outside my scope. {result.reason}"
                )

        return state

    except Exception as e:
        # Assume in scope if check fails
        handle_node_error(state, "scope_checker", e)
        state["scope_check_result"] = ScopeCheckResult(
            is_in_scope=True,
            category="general",
            reason=None,
            confidence=0.5,
        )
        return state
