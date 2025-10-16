"""
Places finder agent - identifies and searches for relevant locations using Google Maps grounding.

Uses ChatVertexAI with a custom Google Maps tool (which wraps genai.Client internally)
to maintain consistency with the rest of the codebase while leveraging real Google Maps data.
"""

from typing import List
from langchain_core.messages import HumanMessage
from langchain_google_vertexai import ChatVertexAI
from pydantic import BaseModel, Field

from ..core.state import AgentState
from ..utils.logging_config import get_logger
from ..utils.model_config import AGENT_MODEL, DEFAULT_TEMPERATURE
from ..utils.config import Config
from ..tools.google_maps import google_maps_search
from ..utils.langfuse_config import trace_node

logger = get_logger(__name__)

# Initialize LLM with explicit project
llm = ChatVertexAI(
    model=AGENT_MODEL,
    temperature=DEFAULT_TEMPERATURE,
    project=Config.GOOGLE_CLOUD_PROJECT,
)


class PlaceType(BaseModel):
    """A type of place to search for."""

    place_type: str = Field(
        description="Type of governmental facility (e.g., 'immigration offices', 'city halls')"
    )
    relevance: str = Field(description="Why this is relevant to the user's situation")


class PlaceTypes(BaseModel):
    """Collection of place types to search for."""

    types: List[PlaceType] = Field(
        description="1-2 types of governmental facilities to search for"
    )


@trace_node("find_useful_places")
def find_useful_places(state: AgentState) -> AgentState:
    """
    Find useful places using Google Maps grounding.

    Uses standard LangChain pattern:
    1. ChatVertexAI identifies relevant place types (structured output)
    2. google_maps_search tool gets real place data (wraps genai.Client)

    This maintains consistency with other nodes while leveraging Google Maps grounding.

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
            logger.info("⏭️  Skipping place search - no Q&A pair")
            return {}

        # Get user's location
        collected_facts = state.get("collected_facts", {})
        location = collected_facts.get("Location", "Tokyo, Japan")

        logger.info(f"📍 Finding useful places near {location}")

        # Step 1: Use LLM to identify relevant place types
        structured_llm = llm.with_structured_output(PlaceTypes)

        prompt = f"""Analyze this Q&A about Japanese procedures and identify 1-2 types of GOVERNMENT OFFICES or PUBLIC ADMINISTRATIVE FACILITIES that would be useful.

User Question: {query_text}

Assistant Answer: {answer_text}

User Location: {location}

IMPORTANT: Use SPECIFIC, NATURAL search terms that work with Google Maps:

GOOD examples:
- "immigration office" (not "Immigration offices/bureaus")
- "city hall" (not "City halls / Ward offices")
- "tax office" (not "Tax offices")
- "Hello Work" (not "Hello Work offices")
- "legal affairs bureau" (not "Legal Affairs Bureau")
- "pension office" (not "Social Insurance offices")

ONLY suggest GOVERNMENTAL facilities:
- Immigration office (出入国在留管理局)
- City hall, ward office (市役所/区役所)
- Tax office (税務署)
- Hello Work (ハローワーク)
- Legal affairs bureau (法務局)
- Pension office (年金事務所)

Rules:
1. Use simple, singular forms (e.g., "city hall" not "city halls / ward offices")
2. Use common English terms people actually search for
3. Be specific to the user's actual need
4. Do NOT suggest private businesses
5. If no relevant government facilities are needed, return an empty list"""

        result = structured_llm.invoke(prompt)

        if not result.types:
            logger.info("ℹ️  No relevant governmental facilities identified")
            return {}

        # Step 2: Search Google Maps for each place type
        all_places = []
        seen_place_ids = set()

        for place_type in result.types[:2]:  # Limit to 2 types
            logger.info(f"   🔍 Searching for: {place_type.place_type}")

            # Call Google Maps search tool
            places = google_maps_search.run(
                {"query": place_type.place_type, "location": location}
            )

            # Add unique places
            for place in places:
                place_id = place.get("place_id")
                if place_id and place_id not in seen_place_ids:
                    all_places.append(place)
                    seen_place_ids.add(place_id)

                # Stop if we have enough places
                if len(all_places) >= 3:
                    break

            if len(all_places) >= 3:
                break

        # Fallback: Add generic search link if we got fewer than 2 places
        if len(all_places) < 2:
            logger.info("   ℹ️  Adding generic search link as fallback")
            search_term = (
                result.types[0].place_type if result.types else "government office"
            )
            search_url = f"https://www.google.com/maps/search/{search_term.replace(' ', '+')}+near+{location.replace(' ', '+')}"
            all_places.append(
                {
                    "name": f"Search for {search_term.title()}",
                    "address": f"View all results near {location}",
                    "place_id": None,
                    "maps_url": search_url,
                }
            )

        # Limit to 3 places total
        all_places = all_places[:3]

        if all_places:
            logger.info(f"✅ Returning {len(all_places)} useful places")
            for place in all_places:
                logger.info(f"   📍 {place['name']}")
            return {"useful_places": all_places}
        else:
            return {}

    except Exception as e:
        # RESILIENT: Log error but return empty dict so main answer still works
        logger.error(f"❌ Error finding places: {e}", exc_info=True)
        logger.info("⚠️  Place search failed, but main answer will still be returned")
        return {}
