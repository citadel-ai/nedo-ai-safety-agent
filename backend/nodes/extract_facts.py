"""
Facts extraction agent - extracts key information ABOUT THE USER's situation.

Focus: USER's context, constraints, preferences, and requirements.
NOT procedural details (those go in the main answer).

DYNAMIC: Decides fact keys based on context, doesn't use hardcoded categories.
"""

from typing import Dict, List
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel, Field
from langchain_google_vertexai import ChatVertexAI

from ..core.state import AgentState
from ..utils.logging_config import get_logger
from ..utils.model_config import AGENT_MODEL, DEFAULT_TEMPERATURE
from ..utils.config import Config
from ..utils.langfuse_config import trace_node

logger = get_logger(__name__)

# Initialize LLM for fact extraction with explicit project
llm = ChatVertexAI(
    model=AGENT_MODEL,
    temperature=DEFAULT_TEMPERATURE,
    project=Config.GOOGLE_CLOUD_PROJECT,
)


class ExtractedFact(BaseModel):
    """A single extracted fact about the user."""

    key: str = Field(
        description="Short descriptive key for this fact (e.g., 'Timeline', 'Family Situation', 'Language Ability')"
    )
    value: str = Field(description="The actual information about the user")
    confidence: str = Field(
        description="'high' if directly stated, 'medium' if inferred, 'low' if uncertain"
    )


class ExtractedFacts(BaseModel):
    """Collection of facts about the user with instructions for merging."""

    facts: List[ExtractedFact] = Field(
        description="List of facts extracted from this conversation turn"
    )
    facts_to_remove: List[str] = Field(
        default=[],
        description="Keys of existing facts that should be removed (if contradicted or no longer relevant)",
    )


@trace_node("extract_facts_from_conversation")
def extract_facts_from_conversation(state: AgentState) -> AgentState:
    """
    Extract key facts ABOUT THE USER from the conversation.

    This agent:
    1. Identifies information about the user's situation, constraints, and preferences
    2. Is AWARE of existing facts and avoids duplication
    3. Can update/overwrite existing facts if new info contradicts old
    4. Dynamically creates fact keys based on context

    RESILIENT: Returns empty dict on error, never breaks the main flow.
    """
    try:
        # Get latest Q&A pair
        query_text = None
        answer_text = state.get("answer", "")

        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                query_text = message.content
                break

        if not query_text or not answer_text:
            logger.info("⏭️  Skipping fact extraction - no Q&A pair")
            return {}

        # Get existing facts to avoid duplication
        existing_facts = state.get("collected_facts", {})
        existing_facts_str = (
            "\n".join([f"- {k}: {v}" for k, v in existing_facts.items()])
            if existing_facts
            else "None yet"
        )

        logger.info(f"📊 Extracting USER facts from conversation")
        logger.info(f"📚 Existing facts: {len(existing_facts)} facts already collected")

        # Use LLM with structured output to extract facts
        structured_llm = llm.with_structured_output(ExtractedFacts)

        prompt = f"""Extract NEW information ABOUT THE USER from this conversation turn.

User Question: {query_text}

Assistant Answer: {answer_text}

EXISTING FACTS ALREADY COLLECTED:
{existing_facts_str}

Your task:
1. Extract ONLY NEW facts about the USER that aren't already captured
2. Create descriptive keys that fit the information (e.g., "Timeline", "Family Situation", "Language Ability", "Budget", "Health Needs")
3. Focus on information about the USER, not procedural details
4. If new info contradicts existing facts, mark old facts for removal

✓ EXTRACT (information about the user):
- Timelines: "Visa expires in March", "Need housing by next month"
- Situation: "Has two young children", "Currently unemployed", "Moving from Osaka"
- Constraints: "Limited Japanese ability", "No car", "Budget under 100,000 yen"
- Preferences: "Prefers morning appointments", "Wants English support"
- Requirements: "Needs wheelchair access", "Must keep current job"
- Background: "First time applying", "Changing from student to work visa"

✗ DON'T EXTRACT (procedural information):
- Office locations, hours, or addresses
- Required documents for the procedure
- Fees or processing times
- Contact information for offices
- General procedure steps

IMPORTANT:
- If a fact is SIMILAR to an existing one, don't duplicate - only add if it's genuinely new info
- If new info CONTRADICTS an existing fact, add the old fact's key to facts_to_remove
- Use clear, concise keys (2-4 words max)
- Don't extract if no relevant user information in this turn

Example keys to create dynamically:
- "Timeline", "Deadline", "Visa Expiry"
- "Family Situation", "Dependents"
- "Language Ability", "Japanese Level"
- "Work Status", "Employment"
- "Budget", "Financial Constraint"
- "Location Preference", "Area"
- "Health Needs", "Accessibility"
- "Previous Experience"
"""

        extracted = structured_llm.invoke(prompt)

        # Process extracted facts
        new_facts = {}
        facts_to_remove = set(extracted.facts_to_remove)

        for fact in extracted.facts:
            # Only add high/medium confidence facts
            if fact.confidence in ["high", "medium"]:
                new_facts[fact.key] = fact.value
                logger.info(
                    f"   ➕ {fact.key}: {fact.value} (confidence: {fact.confidence})"
                )
            else:
                logger.info(f"   ⏭️  Skipping low confidence: {fact.key}")

        # Handle facts to remove (contradictions)
        if facts_to_remove:
            logger.info(f"   🗑️  Facts to remove (contradicted): {facts_to_remove}")
            # We'll handle removal by not including them in the merge
            # Since we use _merge_dicts, we need to explicitly handle deletions
            # For now, just log - removal handled via API endpoint

        if new_facts:
            logger.info(f"✅ Extracted {len(new_facts)} new USER facts")
            return {"collected_facts": new_facts}
        else:
            logger.info("ℹ️  No new USER facts extracted")
            return {}

    except Exception as e:
        # RESILIENT: Log error but return empty dict so main answer still works
        logger.error(f"❌ Error extracting facts: {e}")
        logger.info("⚠️  Fact extraction failed, but main answer will still be returned")
        return {}
