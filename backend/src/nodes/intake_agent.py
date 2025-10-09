"""Intake agent node with memory management and Langfuse v3 observability."""

import logging
import re
import time
import uuid

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_vertexai import ChatVertexAI
from pydantic import ValidationError

from src.intake_suggestions import get_suggestions_for_question
from src.models import IntakeSession, JapanHelpdeskState
from src.settings import load_settings
from src.utils.observability import observe

logger = logging.getLogger(__name__)

# Initialize settings
settings = load_settings()

# Initialize the LLM
llm = ChatVertexAI(
    model=settings.agent_model,
    temperature=settings.agent_temperature,
    max_tokens=settings.agent_max_tokens,
)

# Output parser
parser = PydanticOutputParser(pydantic_object=IntakeSession)


def _extract_json_block(text: str) -> str:
    """Extract JSON content from a model response.

    Supports fenced blocks (```json ... ``` or ``` ... ```). If not found,
    returns the substring between the first '{' and the last '}' if present.
    Otherwise returns the original text.
    """
    try:
        # Prefer a fenced JSON block
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if fenced and fenced.group(1):
            return fenced.group(1).strip()
        # Fallback: best-effort curly braces slice
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1].strip()
    except Exception:
        pass
    return text


# In-memory session storage (in production, use proper database)
session_store: dict[str, IntakeSession] = {}

AUTONOMOUS_INTAKE_PROMPT = """
You are an autonomous intake agent for a Japan helpdesk system. Your role is to intelligently analyze ANY user query and determine what contextual information is needed to provide accurate, personalized assistance.

🧠 AUTONOMOUS CONTEXT ANALYSIS:
For EVERY user query, think through these questions:

1. **WHAT TYPE OF ASSISTANCE?** (Analyze the user's intent)
   - Office/contact information → NEEDS: Location
   - Visa/immigration procedures → NEEDS: Current visa type, expiration date, location
   - Legal procedures (divorce, marriage, etc.) → NEEDS: Location, timeline, current status
   - Financial services (banking, taxes) → NEEDS: Visa type, location, current status
   - Healthcare/insurance → NEEDS: Visa type, location, current coverage
   - Employment issues → NEEDS: Visa type, current status, location
   - Housing/utilities → NEEDS: Location, visa type, timeline
   - General information → MAY NEED: Context depends on specificity

2. **WHAT CONTEXT IS MISSING?** (Dynamic analysis)
   - Does the query mention location? If not, is location needed for this type of request?
   - Does the query mention visa type? If not, do visa rules affect the answer?
   - Does the query mention timeline/urgency? If not, are there time-sensitive aspects?
   - Does the query mention current status? If not, does current situation affect options?

3. **WHAT'S THE MOST CRITICAL MISSING PIECE?** (Prioritization)
   - Location: Critical for office referrals, local procedures, contact information
   - Visa type: Critical for eligibility, available options, required documents
   - Timeline: Critical for urgent matters, deadlines, appointment scheduling
   - Current status: Critical for ongoing procedures, next steps

📊 CURRENT SESSION ANALYSIS:
Session ID: {session_id}
User ID: {user_id}
Current Step: {current_step}
Completed Steps: {completed_steps}
Conversation History: {conversation_history}
Collected Info: {collected_info}

🎯 INTELLIGENT QUESTIONING EXAMPLES:

**Visa Extension Query**: "How do I extend my visa?"
→ ANALYSIS: Needs visa type (different procedures), expiration date (urgency), location (office)
→ QUESTION: "What type of visa are you currently on, and when does it expire? This helps me guide you to the right extension procedure."

**Banking Query**: "How do I open a bank account?"
→ ANALYSIS: Needs visa type (eligibility), location (branch), timeline (urgency)
→ QUESTION: "What type of visa are you on, and which city are you in? Different banks have different requirements for foreign residents."

**Healthcare Query**: "How do I get health insurance?"
→ ANALYSIS: Needs visa type (eligibility), location (office), current coverage (status)
→ QUESTION: "What's your current visa status, and are you currently covered by any insurance? This determines which health insurance options are available to you."

**Employment Query**: "Can I work part-time?"
→ ANALYSIS: Needs visa type (work restrictions), current status (permission status)
→ QUESTION: "What type of visa are you currently on? Work permissions vary significantly by visa type."

🎯 SMART QUESTIONING STRATEGY:
1. **Analyze the query autonomously** - don't rely on keyword matching
2. **Ask for the MOST CRITICAL missing context first**
3. **ONE focused question per turn** - don't overwhelm users
4. **Explain WHY you need the information** - build trust and understanding
5. **Be conversational and empathetic** - this is often stressful for users

{format_instructions}

Process this user input: "{user_input}"

🎯 AUTONOMOUS COMPLETION CRITERIA:
Set is_complete = True when you have enough context to provide:
- **Actionable advice** (not generic information)
- **Location-specific guidance** (if location matters)
- **Visa-appropriate procedures** (if visa status matters)
- **Timeline-appropriate urgency** (if timing matters)
- **Status-appropriate next steps** (if current situation matters)

**THINK AUTONOMOUSLY**: Don't just match keywords. Analyze what the user is actually trying to accomplish and what context would make your response genuinely helpful vs generic.
"""


def get_or_create_session(user_id: str, session_id: str | None = None) -> IntakeSession:
    """Get existing session or create new one."""
    if session_id and session_id in session_store:
        return session_store[session_id]

    # Create new session
    new_session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"
    new_session = IntakeSession(
        session_id=new_session_id,
        user_id=user_id,
        conversation_history=[],
        collected_info={},
        current_step="initial",
        completed_steps=[],
        needs_clarification=[],
        is_complete=False,
    )
    session_store[new_session_id] = new_session
    return new_session


@observe(name="intake_agent_node")
async def intake_agent_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Intake agent node for systematic information gathering."""
    start_time = time.time()

    logger.info(f"🔵 INTAKE AGENT START - Input: '{state['user_input']}'")

    try:
        # Get or create session
        session = get_or_create_session(state["user_id"], state.get("session_id"))

        # Update session with new input
        session.conversation_history.append(f"User: {state['user_input']}")

        # CRITICAL: Set main_request on first interaction if not already set
        if not session.collected_info or "main_request" not in session.collected_info:
            if not session.collected_info:
                session.collected_info = {}
            session.collected_info["main_request"] = state["user_input"]
            logger.info(
                f"🔵 INTAKE AGENT - Set initial main_request: '{state['user_input']}'"
            )

        # Maintain a rolling conversation summary (last ~10 exchanges)
        try:
            recent = "\n".join(session.conversation_history[-10:])
            session.conversation_summary = (
                recent if len(recent) < 1200 else recent[-1200:]
            )
        except Exception:
            pass

        # Prepare the prompt with session context
        format_instructions = parser.get_format_instructions()
        prompt = AUTONOMOUS_INTAKE_PROMPT.format(
            session_id=session.session_id,
            user_id=session.user_id,
            current_step=session.current_step,
            completed_steps=", ".join(session.completed_steps),
            conversation_history=session.conversation_summary
            or "\n".join(session.conversation_history[-10:]),
            collected_info=session.collected_info,
            user_input=state["user_input"],
            format_instructions=format_instructions,
        )

        # Create messages
        messages = [
            SystemMessage(
                content="You are an intake agent for systematic information gathering."
            ),
            HumanMessage(content=prompt),
        ]

        # Get LLM response
        response = await llm.ainvoke(messages)
        content = response.content or ""
        logger.info(f"🔵 INTAKE AGENT - LLM response length: {len(content)} chars")
        logger.info(
            f"🔵 INTAKE AGENT - LLM preview: {content[:300]}{'...' if len(content) > 300 else ''}"
        )

        # Extract robust JSON and parse
        json_text = _extract_json_block(content)
        try:
            updated_session = parser.parse(json_text)
        except Exception as parse_err:
            logger.warning(
                f"🟡 INTAKE AGENT - Primary parse failed, attempting direct Pydantic parse: {parse_err}"
            )
            try:
                updated_session = IntakeSession.model_validate_json(json_text)
            except ValidationError as ve:
                logger.error(f"🔴 INTAKE AGENT - JSON validation failed: {ve}")
                raise

        logger.info(
            f"🔵 INTAKE AGENT - Parsed session: is_complete={updated_session.is_complete}, next_questions={len(updated_session.next_questions)}"
        )
        if updated_session.next_questions:
            logger.info(
                f"🔵 INTAKE AGENT - Questions: {updated_session.next_questions}"
            )
        else:
            logger.warning(
                f"🟡 INTAKE AGENT - next_questions is empty! Required fields: {updated_session.required_context_fields}"
            )

        # Ensure correct session and user IDs
        updated_session.session_id = session.session_id
        updated_session.user_id = session.user_id

        # CRITICAL: Preserve main_request from original session if it exists
        # The LLM might not always include it in collected_info when processing follow-ups
        if session.collected_info and "main_request" in session.collected_info:
            if not updated_session.collected_info:
                updated_session.collected_info = {}
            # Only preserve if the LLM didn't explicitly update it
            if "main_request" not in updated_session.collected_info:
                updated_session.collected_info["main_request"] = session.collected_info[
                    "main_request"
                ]
                logger.info(
                    f"🔵 INTAKE AGENT - Preserved main_request: '{session.collected_info['main_request']}'"
                )

        # Update session store
        session_store[updated_session.session_id] = updated_session

        # Update state
        state["intake_session"] = updated_session
        state["session_id"] = updated_session.session_id
        state["completed_steps"].append("intake")

        # Set final_response based on completion and questions
        if updated_session.next_questions:
            # Has questions to ask (either clarifying questions OR rejection message)
            question = updated_session.next_questions[0]
            state["final_response"] = question
            logger.info(
                f"🔵 INTAKE AGENT - Set final_response from next_questions: '{question[:100]}...'"
            )

            # Generate quick-reply suggestions for this question
            suggestions = get_suggestions_for_question(
                question, updated_session.collected_info
            )
            updated_session.suggested_answers = suggestions
            logger.info(
                f"🔵 INTAKE AGENT - Generated {len(suggestions)} quick-reply suggestions"
            )

            # Add to conversation history
            updated_session.conversation_history.append(f"Agent: {question}")
            session_store[updated_session.session_id] = updated_session
        elif not updated_session.is_complete:
            # No questions but not complete - this shouldn't happen, but handle it
            logger.warning(
                "🟡 INTAKE AGENT - Incomplete but no questions! Continuing workflow..."
            )
        else:
            # Complete and no questions - ready for next stage
            logger.info("🟢 INTAKE AGENT - Complete, proceeding to next stage")

        # Update metadata
        processing_time = time.time() - start_time
        state["processing_time"] += processing_time
        state["tokens_used"] += len(response.content.split())

        # Langfuse v3 automatically captures input/output and timing via @observe decorator
        logger.info(
            f"🔵 INTAKE AGENT END - final_response length: {len(state.get('final_response', '')) if state.get('final_response') else 0}"
        )

        return state

    except Exception as e:
        logger.error(f"🔴 INTAKE AGENT ERROR: {e}", exc_info=True)
        state["errors"].append(f"Intake agent failed: {e!s}")
        state["error_count"] += 1

        # Determine what context might be needed based on keywords
        user_input_lower = state["user_input"].lower()
        next_question = None
        required_fields = []

        if any(
            word in user_input_lower
            for word in ["visa", "extend", "renew", "immigration"]
        ):
            next_question = "To help you with your visa question, could you tell me: What type of visa are you currently on, and when does it expire?"
            required_fields = ["visa_type", "timeline"]
        elif any(
            word in user_input_lower for word in ["office", "where", "which", "contact"]
        ):
            next_question = "To direct you to the right office, which city or prefecture in Japan are you located in?"
            required_fields = ["user_location"]
        elif any(word in user_input_lower for word in ["work", "job", "employment"]):
            next_question = "To advise you on work-related matters, what type of visa are you currently on?"
            required_fields = ["visa_type"]
        elif any(word in user_input_lower for word in ["bank", "account", "money"]):
            next_question = "To help you with banking, what type of visa are you on, and which city are you in?"
            required_fields = ["visa_type", "user_location"]
        else:
            # Generic fallback question
            next_question = "To provide you with accurate information, could you tell me: What type of visa are you on, and which city in Japan are you located in?"
            required_fields = ["visa_type", "user_location"]

            # Create fallback session with helpful question
            # Generate suggestions for the fallback question
            suggestions = (
                get_suggestions_for_question(next_question) if next_question else []
            )

            fallback_session = IntakeSession(
                session_id=state.get("session_id", f"fallback_{uuid.uuid4().hex[:8]}"),
                user_id=state["user_id"],
                conversation_history=[f"User: {state['user_input']}"],
                collected_info={"main_request": state["user_input"]},
                current_step="basic_info",
                completed_steps=["initial"],
                needs_clarification=required_fields,
                is_complete=False,
                required_context_fields=required_fields,
                missing_context_fields=required_fields,
                next_questions=[next_question] if next_question else [],
                suggested_answers=suggestions,
            )

        state["intake_session"] = fallback_session
        state["session_id"] = fallback_session.session_id

        # Set the fallback question as final response
        if next_question:
            state["final_response"] = next_question
            logger.info(
                f"🟡 INTAKE AGENT FALLBACK - Set fallback question: '{next_question}'"
            )
        else:
            logger.error("🔴 INTAKE AGENT FALLBACK - No fallback question generated!")

        # Langfuse v3 automatically captures exceptions via @observe decorator

        return state
