"""Vertex AI Search tool configuration using the Summary API.

Provides two pre-built tool instances:
* ``vertex_search_tool`` -- returns a human-readable summary.
* ``vertex_search_raw_tool`` -- returns the raw protobuf response for
  citation extraction.
"""

from typing import Any

from langchain_google_community.vertex_ai_search import VertexAISearchSummaryTool

from ..utils.config import Config
from .prompts import SEARCH_SYSTEM_PROMPT

# Shared configuration for both the summary and raw-response tools.
_COMMON_KWARGS: dict[str, Any] = {
    "project_id": Config.GOOGLE_CLOUD_PROJECT,
    "data_store_id": Config.VERTEX_AI_SEARCH_DATA_STORE_ID,
    "location_id": "global",
    "engine_data_type": 0,
    "summary_result_count": 5,
    "summary_include_citations": True,
    "get_extractive_answers": False,
    "max_extractive_segment_count": 3,
    "return_extractive_segment_score": True,
    "num_previous_segments": 1,
    "num_next_segments": 1,
    "summary_spec_kwargs": {
        "language_code": "en",
        "ignore_adversarial_query": True,
        "ignore_jail_breaking_query": True,
        "ignore_low_relevant_content": True,
        "use_semantic_chunks": True,
    },
    "summary_prompt": SEARCH_SYSTEM_PROMPT,
}


class VertexAISearchRawTool(VertexAISearchSummaryTool):
    """Variant that returns the raw search response for citation extraction."""

    def _run(self, query: str) -> Any:
        request = self._create_search_request(query)
        return self._client.search(request)


vertex_search_tool = VertexAISearchSummaryTool(
    **_COMMON_KWARGS,
    name="Japan Procedures Search",
    description="Search for information about official procedures in Japan",
)

vertex_search_raw_tool = VertexAISearchRawTool(
    **_COMMON_KWARGS,
    name="Japan Procedures Search (Raw)",
    description="Search for information with full citation metadata",
)
