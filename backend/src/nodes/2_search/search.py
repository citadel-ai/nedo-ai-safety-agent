"""Agentic Search Orchestrator - Multi-query intelligent search with ranking."""

import asyncio
import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI

from src.services.enhanced_google_search import get_enhanced_search_results
from src.core.models import JapanHelpdeskState, MergedSearchResult
from src.core.settings import load_settings
from src.utils.observability import observe

# Initialize settings
settings = load_settings()

# Initialize LLM for query generation
llm = ChatVertexAI(
    model=settings.agent_model,
    temperature=settings.agent_temperature,
    max_tokens=512,
    location=settings.vertex_ai_location,
)

logger = logging.getLogger(__name__)

QUERY_VARIANT_PROMPT = """
You are a search query expert for Japan. Generate multiple search query variants in BOTH English and Japanese.

**Original Query**: "{original_query}"
**User Context**: {context}

**Your Task**: Generate 4-6 search query variants (half in English, half in Japanese) that approach this question from different angles.

**Guidelines**:
1. Use different terminology (e.g., "renewal" vs "extension" vs "application")
2. Include specific aspects (requirements, procedure, documents, timeline, location)
3. **CRITICAL**: Generate BOTH English AND Japanese variants
4. Keep queries focused and searchable (5-10 words each)
5. Cover different information needs (what, how, where, when)
6. For Japanese queries, use natural Japanese terms used in official contexts

**Examples**:

Original: "How do I renew my visa?"
Variants:
1. visa renewal procedure immigration office
2. visa extension requirements documents timeline
3. ビザ更新 手続き 入管
4. 在留資格 更新 申請方法
5. residence status renewal application
6. immigration services visa extension Japan

Original: "Where do I register my marriage?"
Variants:
1. marriage registration city hall ward office
2. marriage certificate international couple Japan
3. 婚姻届 市役所 手続き
4. 国際結婚 届出 必要書類
5. konin todoke ward office procedure
6. marriage registration documents required

**IMPORTANT**:
- At least 2-3 queries MUST be in Japanese (using kanji and hiragana)
- Japanese queries should use official terminology (入管, 在留資格, 市役所, etc.)
- Official Japanese government sites have the most accurate information

**Return ONLY the query variants, one per line, numbered. No explanations.**
"""


@observe(name="generate_query_variants")
async def generate_query_variants(
    original_query: str, context: dict[str, Any]
) -> list[str]:
    """Generate multiple query variants using LLM."""

    import logging

    logger = logging.getLogger(__name__)

    try:
        # Format context
        context_str = (
            ", ".join([f"{k}: {v}" for k, v in context.items()])
            if context
            else "No context"
        )

        prompt = QUERY_VARIANT_PROMPT.format(
            original_query=original_query, context=context_str
        )

        messages = [
            SystemMessage(content="You are a search query expert."),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)

        # Parse variants (one per line, numbered)
        lines = response.content.strip().split("\n")
        variants = []
        for line in lines:
            # Remove numbering (1., 2., etc.) and clean
            clean = line.strip()
            if clean and any(c.isalpha() for c in clean):
                # Remove leading numbers and dots
                clean = clean.lstrip("0123456789. ")
                if clean:
                    variants.append(clean)

        # Always include original query as fallback
        if original_query not in variants:
            variants.insert(0, original_query)

        logger.info(
            f"🔍 Generated {len(variants)} query variants (English + Japanese):"
        )
        for i, variant in enumerate(variants, 1):
            logger.info(f"   {i}. {variant}")
        return variants[:6]  # Max 6 variants (3 English + 3 Japanese)

    except Exception as e:
        logger.error(f"🔴 Query variant generation failed: {e}")
        # Fallback to original query
        return [original_query]


async def enhance_query_for_google(query: str, context: dict[str, Any]) -> str:
    """Enhance query for Google Search with appropriate handling for Japanese and English queries."""

    enhanced = query

    # Detect if query is primarily Japanese
    has_japanese = any(
        "\u3040" <= char <= "\u30ff" or "\u4e00" <= char <= "\u9faf" for char in query
    )

    # Add location if available and not already in query
    location = context.get("location")
    if location and location.lower() not in query.lower():
        if has_japanese:
            enhanced = f"{enhanced} {location}"
        else:
            enhanced = f"{enhanced} {location}"

    # For English queries, add Japan context
    # For Japanese queries, it's already implicit
    if not has_japanese and "japan" not in enhanced.lower() and "日本" not in enhanced:
        enhanced = f"{enhanced} Japan"

    return enhanced


def build_search_context(state: JapanHelpdeskState) -> dict[str, Any]:
    """Extract search context from intake session."""
    context = {}
    intake = state.get("intake_session")
    
    if intake:
        if hasattr(intake, "visa_type") and intake.visa_type:
            context["visa_type"] = intake.visa_type
        if hasattr(intake, "user_location") and intake.user_location:
            context["location"] = intake.user_location
        if hasattr(intake, "timeline") and intake.timeline:
            context["timeline"] = intake.timeline
    
    return context


async def execute_parallel_searches(
    query_variants: list[str], context: dict[str, Any]
) -> list[tuple[str, str, Any]]:
    """
    Execute parallel searches for query variants.
    
    Returns:
        List of (source_type, query, result) tuples
    """
    search_tasks = []
    
    # Use up to 4 variants (mix of English and Japanese)
    for i, query in enumerate(query_variants[:4], 1):
        logger.info(f"🔍 Variant {i}: '{query}'")
        
        # Google search with enhanced query
        google_query = await enhance_query_for_google(query, context)
        logger.info(f"🌐 Google variant {i}: '{google_query}'")
        
        search_tasks.append(
            (
                "google",
                google_query,
                get_enhanced_search_results(google_query, num_results=4),
            )
        )
    
    logger.info(f"⚡ Executing {len(search_tasks)} parallel searches...")
    results = await asyncio.gather(
        *[task[2] for task in search_tasks], return_exceptions=True
    )
    
    # Combine tasks with results
    return [
        (search_tasks[j][0], search_tasks[j][1], results[j])
        for j in range(len(search_tasks))
    ]


def deduplicate_vector_results(vector_results: list[Any]) -> list[Any]:
    """Deduplicate vector search results by content hash."""
    unique_results = []
    seen_contents = set()
    
    for res in vector_results:
        content = res.content if hasattr(res, "content") else str(res)
        content_hash = hash(content[:100])
        
        if content_hash not in seen_contents:
            seen_contents.add(content_hash)
            unique_results.append(res)
    
    return unique_results


def deduplicate_google_results(google_results: list[Any]) -> list[Any]:
    """Deduplicate Google search results by URL."""
    unique_results = []
    seen_urls = set()
    
    for res in google_results:
        url = getattr(res, "url", "") if hasattr(res, "url") else str(res)
        
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(res)
    
    return unique_results


def convert_google_results_to_strings(google_results: list[Any]) -> list[str]:
    """Convert Google result objects to formatted strings with content."""
    results_str = []
    
    for res in google_results:
        if hasattr(res, "title"):
            # Build a rich string with title, URL, and full_content
            title = res.title if isinstance(res.title, str) else str(res.title)
            url = res.url if isinstance(res.url, str) else str(res.url)
            snippet = res.snippet if isinstance(res.snippet, str) else str(res.snippet)
            full_content = getattr(res, "full_content", None)
            
            # Build rich string with all available info
            result_str = f"Title: {title}\nURL: {url}\n"
            if full_content and len(full_content) > 100:
                result_str += f"Content: {full_content[:2000]}...\n"
            elif snippet:
                result_str += f"Snippet: {snippet}\n"
            
            results_str.append(result_str)
            logger.info(
                f"📊 Converted Google result to string ({len(result_str)} chars, "
                f"has_full_content: {bool(full_content)})"
            )
        elif isinstance(res, str):
            results_str.append(res)
        else:
            results_str.append(str(res))
    
    return results_str


def log_search_results_detail(
    unique_google: list[Any], unique_vector: list[Any]
) -> None:
    """Log detailed information about search results."""
    # Log Google results
    logger.info("📊 GOOGLE SEARCH RESULTS DETAIL:")
    for i, res in enumerate(unique_google[:3], 1):  # Show first 3
        if hasattr(res, "title"):
            title = res.title() if callable(res.title) else res.title
            url = (
                res.url()
                if callable(getattr(res, "url", None))
                else getattr(res, "url", "N/A")
            )
            content = (
                res.content()
                if callable(getattr(res, "content", None))
                else getattr(res, "content", "N/A")
            )
            logger.info(f"   {i}. Title: {title}")
            logger.info(f"      URL: {url}")
            logger.info(f"      Content preview: {str(content)[:200]}...")
        elif isinstance(res, str):
            logger.info(f"   {i}. (String result): {res[:200]}...")
        else:
            logger.info(
                f"   {i}. (Unknown type: {type(res).__name__}): {str(res)[:200]}..."
            )
    
    # Log Vector results
    logger.info("📊 VECTOR SEARCH RESULTS DETAIL:")
    for i, res in enumerate(unique_vector[:3], 1):  # Show first 3
        if hasattr(res, "content"):
            logger.info(f"   {i}. Content: {res.content[:150]}...")
            logger.info(f"      Source: {getattr(res, 'source', 'N/A')}")
            logger.info(f"      Score: {getattr(res, 'similarity_score', 'N/A')}")
        else:
            logger.info(f"   {i}. {str(res)[:200]}...")


def extract_sources_from_results(
    unique_vector: list[Any], unique_google: list[Any]
) -> list[str]:
    """Extract source URLs/identifiers from search results."""
    sources = []
    
    # Extract from vector results
    for res in unique_vector:
        if hasattr(res, "source"):
            sources.append(res.source)
    
    # Extract from Google results
    for res in unique_google:
        if hasattr(res, "url"):
            sources.append(res.url)
        elif isinstance(res, str):
            sources.append(res)
    
    return sources


def create_merged_search_result(
    unique_vector: list[Any],
    unique_google: list[Any],
    google_results_str: list[str],
    sources: list[str],
) -> MergedSearchResult:
    """Create a unified search result from vector and Google results."""
    total_results = len(unique_vector) + len(unique_google)
    
    return MergedSearchResult(
        vector_results=unique_vector,
        google_results=google_results_str,
        merged_summary=f"Found {total_results} results from multi-query bilingual search (English + Japanese)",
        confidence_score=0.8 if (unique_vector or unique_google) else 0.2,
        sources=sources[:10],  # Limit to top 10 sources
        recommendations=[],
    )


@observe(name="search_node")
async def search_node(
    state: JapanHelpdeskState,
) -> JapanHelpdeskState:
    """
    Search node with multi-query strategy.
    Generates multiple query variants and executes parallel searches for comprehensive results.
    """
    start_time = time.time()

    try:
        # Get the synthesized query (or fall back to user input)
        base_query = state.get("synthesized_search_query") or state["user_input"]
        
        # Build context from intake session
        context = build_search_context(state)
        
        logger.info(f"🔍 AGENTIC SEARCH - Base query: '{base_query}'")
        logger.info(f"🔍 AGENTIC SEARCH - Context: {context}")

        # Generate multiple query variants (English + Japanese)
        query_variants = await generate_query_variants(base_query, context)
        logger.info(f"🔍 AGENTIC SEARCH - Generated {len(query_variants)} variants")

        # Execute parallel searches for all variants
        search_results = await execute_parallel_searches(query_variants, context)

        # Organize results by source type
        vector_results = []
        google_results = []

        for source_type, query, result in search_results:
            if isinstance(result, Exception):
                logger.warning(f"⚠️ Search failed for '{query}': {result}")
                continue

            if source_type == "vector" and result:
                vector_results.extend(result)
                logger.info(f"📊 Vector search '{query}': {len(result)} results")
            elif source_type == "google" and result:
                google_results.extend(result)
                logger.info(f"🌐 Google search '{query}': {len(result)} results")

        # Deduplicate results
        unique_vector = deduplicate_vector_results(vector_results)
        unique_google = deduplicate_google_results(google_results)

        # Log summary
        logger.info("✅ AGENTIC SEARCH COMPLETE:")
        logger.info(f"   Vector results: {len(unique_vector)} unique")
        logger.info(f"   Google results: {len(unique_google)} unique")
        logger.info(f"   Total: {len(unique_vector) + len(unique_google)} results")

        # Log detailed results for debugging
        log_search_results_detail(unique_google, unique_vector)

        # Extract sources and convert Google results to strings
        sources = extract_sources_from_results(unique_vector, unique_google)
        google_results_str = convert_google_results_to_strings(unique_google)

        # Create unified search result
        merged_result = create_merged_search_result(
            unique_vector, unique_google, google_results_str, sources
        )

        # Update state with results
        state["hybrid_results"] = merged_result
        state["vector_results"] = merged_result  # For compatibility
        state["_raw_vector_results"] = unique_vector
        state["_raw_google_results"] = google_results_str

        # Update metadata
        processing_time = time.time() - start_time
        state["processing_time"] += processing_time
        state["completed_steps"].append("agentic_search")

        logger.info(f"⏱️ Agentic search completed in {processing_time:.2f}s")

        return state

    except Exception as e:
        logger.error(f"🔴 AGENTIC SEARCH ERROR: {e}", exc_info=True)
        state["errors"].append(f"Agentic search failed: {e!s}")
        state["error_count"] += 1
        return state
