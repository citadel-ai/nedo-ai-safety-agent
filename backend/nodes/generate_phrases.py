"""
Phrases generator agent - creates contextually relevant Japanese phrases.
"""

from typing import List
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from langchain_google_vertexai import ChatVertexAI

from ..core.state import AgentState
from ..utils.logging_config import get_logger
from ..utils.model_config import AGENT_MODEL, CREATIVE_TEMPERATURE
from ..utils.config import Config
from ..utils.langfuse_config import trace_node

logger = get_logger(__name__)

# Initialize LLM for phrase generation with explicit project
llm = ChatVertexAI(
    model=AGENT_MODEL,
    temperature=CREATIVE_TEMPERATURE,
    project=Config.GOOGLE_CLOUD_PROJECT,
)


class JapanesePhrase(BaseModel):
    """Single Japanese phrase with translations."""

    japanese: str = Field(
        description="Japanese phrase in hiragana/katakana/kanji, WITHOUT romaji"
    )
    romaji: str = Field(description="Romanization (romaji) of the phrase")
    english: str = Field(description="English translation")


class UsefulPhrases(BaseModel):
    """Collection of useful Japanese terms and forms."""

    phrases: List[JapanesePhrase] = Field(
        description="List of 3-5 key nouns, compound nouns, and verb forms"
    )


@trace_node("generate_useful_phrases")
def generate_useful_phrases(state: AgentState) -> AgentState:
    """
    Generate 3-5 key Japanese terms and forms (nouns, compound nouns, verb forms).

    Analyzes the query AND answer to extract essential vocabulary the user
    will encounter in official contexts for that specific procedure.

    RESILIENT: Returns empty dict on error, never breaks the main flow.
    """
    try:
        # Get latest query and answer
        query_text = None
        answer_text = state.get("answer", "")

        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                query_text = message.content
                break

        if not query_text or not answer_text:
            logger.info("⏭️  Skipping phrase generation - no Q&A pair")
            return {}

        # Get user's collected facts for context
        collected_facts = state.get("collected_facts", {})
        visa_type = collected_facts.get("Visa Type", "")
        location = collected_facts.get("Location", "")

        logger.info(f"💬 Generating useful phrases for topic")

        # Use LLM with structured output
        structured_llm = llm.with_structured_output(UsefulPhrases)

        context_info = (
            f"User context: {visa_type} visa in {location}"
            if visa_type and location
            else ""
        )

        prompt = f"""Generate 3-5 key Japanese terms and forms for someone dealing with this situation.

User query: {query_text}
Assistant answer: {answer_text}
{context_info}

Focus on NOUNS, COMPOUND NOUNS, and VERB FORMS that are specific to this procedure.

✓ GOOD (what to generate):
- 国民健康保険に加入する (kokumin kenkou hoken ni kanyuu suru) - Enroll in National Health Insurance
- 在留カード (zairyuu kaado) - Residence Card
- 申請書類 (shinsei shorui) - Application Documents
- 更新手続き (koushin tetsuzuki) - Renewal Procedure
- 必要書類 (hitsuyou shorui) - Required Documents

✗ BAD (avoid):
- Simple conversational phrases like "Thank you"
- Question phrases like "Where is...?"
- Generic greetings

Generate terms that are:
1. Specific technical/administrative vocabulary for this procedure
2. Key compound nouns used in official contexts
3. Important verb forms (ーする forms) for actions they need to take
4. Terms they'll see on forms or hear at offices

Limit: 3-5 terms maximum.
Provide romaji (romanization) using Hepburn style.
"""

        result = structured_llm.invoke(prompt)

        phrases_list = []
        for phrase in result.phrases[:5]:  # Limit to 5
            phrases_list.append(
                {
                    "japanese": phrase.japanese,
                    "romaji": phrase.romaji,
                    "english": phrase.english,
                }
            )
            logger.info(f"   💬 {phrase.english}: {phrase.japanese}")

        if phrases_list:
            logger.info(f"✅ Generated {len(phrases_list)} useful phrases")
            return {"useful_phrases": phrases_list}
        else:
            return {}

    except Exception as e:
        # RESILIENT: Log error but return empty dict so main answer still works
        logger.error(f"❌ Error generating phrases: {e}")
        logger.info(
            "⚠️  Phrase generation failed, but main answer will still be returned"
        )
        return {}
