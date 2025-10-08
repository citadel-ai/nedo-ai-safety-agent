# Copyright 2025 Google LLC

"""Vector RAG node for LangGraph with Langfuse observability."""

import time

from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_vertexai import ChatVertexAI

from src.models import JapanHelpdeskState, MergedSearchResult
from src.real_vector_db import real_vector_search
from src.utils.observability import observe

llm = ChatVertexAI(model="gemini-2.5-flash", temperature=0.1, location="us-central1")
parser = PydanticOutputParser(pydantic_object=MergedSearchResult)


@observe(name="vector_rag_node")
async def vector_rag_node(state: JapanHelpdeskState) -> JapanHelpdeskState:
    """Vector RAG search node."""
    start_time = time.time()

    try:
        # Prefer synthesized query; fall back to user input and augment with intake context
        query = state.get("synthesized_search_query") or state["user_input"]
        intake = state.get("intake_session")
        if intake and getattr(intake, "collected_info", None):
            main_request = intake.collected_info.get("main_request")
            location = intake.collected_info.get("location") or getattr(
                intake, "user_location", None
            )
            if main_request and main_request != query:
                query = f"{main_request}: {query}"
            if location:
                query = f"{query} in {location}"
        vector_results = await real_vector_search(query)
        # Re-rank and keep top-3
        if vector_results:
            vector_results = sorted(
                vector_results, key=lambda r: r.similarity_score, reverse=True
            )[:3]

        # Langfuse v3 automatically captures context via @observe decorator

        # Create grounded summary with inline citations
        if vector_results:
            citations = []
            for idx, r in enumerate(vector_results, start=1):
                snippet = r.content[:240].rstrip()
                citations.append(
                    f"[{idx}] {snippet} (Source: {r.source}, Score: {r.similarity_score:.2f})"
                )
            summary = "\n".join(citations)
            confidence = sum(r.similarity_score for r in vector_results) / len(
                vector_results
            )
            sources = [r.source for r in vector_results]
        else:
            summary = "No relevant information found in the official documentation."
            confidence = 0.0
            sources = []

        result = MergedSearchResult(
            vector_results=vector_results,
            google_results=[],
            merged_summary=summary,
            confidence_score=confidence,
            sources=sources,
            recommendations=[
                "Verify with official sources",
                "Contact relevant government office",
            ],
        )

        state["vector_results"] = result
        state["completed_steps"].append("vector_rag")
        state["sources"].extend(result.sources)

        processing_time = time.time() - start_time
        state["processing_time"] += processing_time

        # Langfuse v3 automatically captures output via @observe decorator

        return state

    except Exception as e:
        state["errors"].append(f"Vector RAG failed: {e!s}")
        state["error_count"] += 1
        # Langfuse v3 automatically captures exceptions via @observe decorator
        return state
