"""Hybrid search node combining vector DB and Google Search with Langfuse v3 observability."""

import asyncio
import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_vertexai import ChatVertexAI

from app.enhanced_google_search import get_enhanced_search_results
from app.real_vector_db import real_vector_search
from app.types import JapanHelpdeskState, MergedSearchResult
from app.utils.observability import observe

# Initialize the LLM
llm = ChatVertexAI(
    model="gemini-2.5-flash", temperature=0.2, max_tokens=3072, location="us-central1"
)

# Output parser
parser = PydanticOutputParser(pydantic_object=MergedSearchResult)

HYBRID_SEARCH_PROMPT = """
You are a hybrid search agent that combines vector database and Google Search results.

SEARCH STRATEGY:
1. Use vector database for curated, official information
2. Use Google Search for current and supplementary information
3. Intelligently merge results from both sources
4. Resolve conflicts between different information sources
5. Provide comprehensive, well-sourced responses

VECTOR DATABASE RESULTS:
{vector_results}

GOOGLE SEARCH RESULTS:
{google_results}

MERGE METHODOLOGY:
- Use complementary information to build complete picture
- Cross-reference facts between sources
- Favor newer information for time-sensitive topics
- Give higher weight to official government sources
- Use Google Search to fill vector DB gaps

{format_instructions}

Query: "{query}"
Provide a comprehensive merged response with high-quality recommendations.
"""


@observe(name="hybrid_search_node")
async def hybrid_search_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Hybrid search node combining vector DB and Google Search."""

    import logging

    logger = logging.getLogger(__name__)

    start_time = time.time()

    # Use synthesized query if available, augmented with intake context
    query = state.get("synthesized_search_query") or state["user_input"]
    intake = state.get("intake_session")
    if intake and getattr(intake, "collected_info", None):
        main_request = intake.collected_info.get("main_request")
        location = intake.collected_info.get("location") or getattr(
            intake, "user_location", None
        )
        if main_request and main_request != query:
            query = f"{main_request}: {query}"
        if location and location.lower() not in query.lower():
            query = f"{query} in {location}"
    logger.info(f"🔎 HYBRID SEARCH - Using synthesized/augmented query: '{query}'")

    try:
        # Execute both searches in parallel
        vector_task = asyncio.create_task(real_vector_search(query))
        google_task = asyncio.create_task(
            get_enhanced_search_results(query, num_results=5)
        )

        vector_results, google_results = await asyncio.gather(vector_task, google_task)

        # Format results for the prompt
        vector_results_text = (
            "\n".join(
                [
                    f"- {result.content[:200]}... (Score: {result.similarity_score:.2f}, Source: {result.source})"
                    for result in vector_results
                ]
            )
            if vector_results
            else "No vector database results found."
        )

        google_results_text = (
            "\n".join([f"- {result}" for result in google_results])
            if google_results
            else "No Google search results found."
        )

        # Prepare the prompt
        format_instructions = parser.get_format_instructions()
        prompt = HYBRID_SEARCH_PROMPT.format(
            vector_results=vector_results_text,
            google_results=google_results_text,
            query=query,
            format_instructions=format_instructions,
        )

        # Create messages
        messages = [
            SystemMessage(
                content="You are a hybrid search agent combining multiple information sources."
            ),
            HumanMessage(content=prompt),
        ]

        # Get LLM response
        response = await llm.ainvoke(messages)

        # Parse the response
        merged_result = parser.parse(response.content)

        # Ensure we have the actual search results in the response
        merged_result.vector_results = vector_results
        merged_result.google_results = google_results

        # Update state
        state["hybrid_results"] = merged_result
        state["completed_steps"].append("hybrid_search")
        state["sources"].extend(merged_result.sources)
        state["recommendations"].extend(merged_result.recommendations)

        # Update metadata
        processing_time = time.time() - start_time
        state["processing_time"] += processing_time
        state["tokens_used"] += len(response.content.split())

        # Langfuse v3 automatically captures input/output and timing via @observe decorator

        return state

    except Exception as e:
        state["errors"].append(f"Hybrid search failed: {e!s}")
        state["error_count"] += 1

        # Create fallback result
        fallback_result = MergedSearchResult(
            vector_results=[],
            google_results=[],
            merged_summary=f"Search failed for query: {query}. Please try rephrasing your question or contact the relevant government office directly.",
            confidence_score=0.0,
            sources=["error_fallback"],
            recommendations=[
                "Try rephrasing your query",
                "Contact support if the issue persists",
                "Visit official government websites for the most current information",
            ],
        )

        state["hybrid_results"] = fallback_result

        # Langfuse v3 automatically captures exceptions via @observe decorator

        return state
