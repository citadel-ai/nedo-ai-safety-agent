# Copyright 2025 Google LLC

"""Scope checker node for LangGraph with Langfuse v3 observability."""

import re
import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_vertexai import ChatVertexAI

from app.types import SUPPORTED_CATEGORIES, JapanHelpdeskState, ScopeCheckResult
from app.utils.observability import observe

llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.0, location="us-central1")
parser = PydanticOutputParser(pydantic_object=ScopeCheckResult)

SCOPE_CHECK_PROMPT = """
Determine if this user request is within scope for a Japan Helpdesk system. Use the overall conversation context, not only the latest short reply.

IN SCOPE: visa, immigration, housing, tax, employment, healthcare, banking, education, marriage, driving, residence card, pension, insurance, business registration, general procedures.

OUT OF SCOPE: illegal activities (e.g., tax evasion, forged documents, bribery), specific legal advice, medical advice, investment advice, non-Japan related queries.

IMPORTANT:
- If the latest user message is a short answer to a follow-up question (e.g., just a location like "Tokyo"), treat it as context and evaluate scope based on the user's main request and collected context.
- Prefer the synthesized or main user intent over the latest short message when determining scope.
- If the intent appears to be illegal or to bypass laws (e.g., "how to avoid taxes", "how to evade taxes", "how to fake documents"), classify as OUT OF SCOPE with a clear reason.

EXAMPLES:
- "How do I avoid taxes?" → OUT OF SCOPE (illegal intent)
- "How to evade taxes in Japan?" → OUT OF SCOPE (illegal intent)
- "What documents do I need for address registration?" → IN SCOPE (general procedures)
- Latest: "Tokyo" with earlier intent "student visa renewal" → IN SCOPE (treat "Tokyo" as context)

{format_instructions}

Context: {context}
Evaluated Query: "{query}"
"""


@observe(name="scope_checker_node")
async def scope_checker_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Check if query is within supported scope."""
    start_time = time.time()

    # Langfuse v3 automatically captures function context via @observe decorator

    try:
        # Build an evaluated query using synthesized intent and intake context
        intake = state.get("intake_session")
        collected = getattr(intake, "collected_info", {}) if intake else {}
        main_request = collected.get("main_request")
        location = collected.get("location") or (
            getattr(intake, "user_location", None) if intake else None
        )
        visa_type = getattr(intake, "visa_type", None) if intake else None
        latest = state["user_input"]
        synthesized = state.get("synthesized_search_query")

        # Start with synthesized or main request, fallback to latest
        evaluated_query = synthesized or main_request or latest
        # If latest looks like a short context answer, incorporate it as context
        if (
            main_request
            and latest
            and len(latest.split()) <= 3
            and latest.lower() not in {"yes", "no"}
        ):
            if not location:
                location = latest

        # Deterministic override: short context reply with clear main intent → mark in-scope
        def _classify_category(text: str) -> str:
            text_l = (text or "").lower()
            if any(
                k in text_l
                for k in [
                    "visa",
                    "immigration",
                    "residence card",
                    "status of residence",
                ]
            ):
                return "visa"
            if any(k in text_l for k in ["housing", "rental", "apartment", "lease"]):
                return "housing"
            if any(k in text_l for k in ["tax", "taxes", "withholding", "my number"]):
                return "tax"
            if any(
                k in text_l for k in ["work", "employment", "job", "part-time", "baito"]
            ):
                return "employment"
            if any(
                k in text_l
                for k in ["health", "insurance", "clinic", "hospital", "nhis"]
            ):
                return "healthcare"
            if any(k in text_l for k in ["bank", "account", "atm", "transfer"]):
                return "banking"
            if any(
                k in text_l for k in ["school", "education", "university", "enrollment"]
            ):
                return "education"
            if any(
                k in text_l for k in ["marriage", "divorce", "koseki", "registration"]
            ):
                return "marriage"
            if any(k in text_l for k in ["license", "driving", "jaf", "convert"]):
                return "driving_license"
            if any(k in text_l for k in ["pension", "nenkin"]):
                return "pension"
            if any(k in text_l for k in ["insurance", "national health", "kokumin"]):
                return "insurance"
            if any(
                k in text_l
                for k in ["business", "company", "registration", "incorporate"]
            ):
                return "business_registration"
            return "general_procedures"

        is_short_context_reply = (
            latest and len(latest.split()) <= 3 and latest.lower() not in {"yes", "no"}
        )
        if (synthesized or main_request) and is_short_context_reply:
            category = _classify_category(synthesized or main_request)
            # Only override if category is supported
            if category in SUPPORTED_CATEGORIES:
                result = ScopeCheckResult(
                    is_in_scope=True, category=category, reason=None, confidence=0.9
                )
                state["scope_check_result"] = result
                state["completed_steps"].append("scope_check")
                return state

        # Build LLM context using rolling summary when available
        summary = getattr(intake, "conversation_summary", "") if intake else ""
        context = {
            "main_request": main_request or evaluated_query,
            "location": location,
            "visa_type": visa_type,
            "latest_user_message": latest,
            "conversation_summary": summary,
            "synthesized_search_query": synthesized,
        }

        # Deterministic illegal/unethical intent filter (fail-closed)
        combined_text = f"{evaluated_query} {latest}".lower()
        phrase_hits = [
            "tax evasion",
            "bypass the law",
            "cheat the system",
            "forged",
            "fake",
            "bribe",
            "illegally",
        ]
        regex_hits = [
            r"\bavoid(ing)?\s+tax(es)?\b",
            r"\bevad(e|ing|ed)\s+tax(es)?\b",
            r"\bdodg(e|ing|ed)\s+tax(es)?\b",
            r"\bcheat(ing)?\s+tax(es)?\b",
        ]
        illegal_match = any(p in combined_text for p in phrase_hits) or any(
            re.search(rx, combined_text) for rx in regex_hits
        )
        if illegal_match:
            result = ScopeCheckResult(
                is_in_scope=False,
                category=None,
                reason="Request appears to seek illegal activity (e.g., tax evasion), which is out of scope.",
                confidence=0.95,
            )
            state["scope_check_result"] = result
            state["completed_steps"].append("scope_check")
            return state

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
        state["completed_steps"].append("scope_check")

        if not result.is_in_scope:
            state["final_response"] = (
                f"I'm sorry, but your query is outside my scope. {result.reason}"
            )

        processing_time = time.time() - start_time
        state["processing_time"] += processing_time
        state["tokens_used"] += len(response.content.split())

        # Langfuse v3 automatically captures output via @observe decorator

        return state

    except Exception as e:
        state["errors"].append(f"Scope check failed: {e!s}")
        state["error_count"] += 1

        # Assume in scope if check fails
        state["scope_check_result"] = ScopeCheckResult(
            is_in_scope=True, category="general", reason=None, confidence=0.5
        )

        # Langfuse v3 automatically captures exceptions via @observe decorator
        return state
