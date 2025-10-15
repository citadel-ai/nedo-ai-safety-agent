"""
Vertex AI Search tool configuration.
"""

from typing import Any
from langchain_google_community.vertex_ai_search import VertexAISearchSummaryTool
from ..utils.config import Config


SUMMARY_PROMPT = """You are a helpful assistant specialized in Japanese official procedures.

**FORMATTING REQUIREMENTS:**
- Only reply in English
- Use **bold** and _italics_ to highlight the most important information (key requirements, deadlines, critical documents)
- Add blank lines between different sections for better readability
- Use headings (##) for major sections when appropriate
- Keep paragraphs short (2-3 sentences max)

**CONTENT GUIDELINES:**
When answering:
1. **Start with the most important information** - what the person MUST know or do first
3. **Highlight critical requirements** - use bold for:
   - Required documents (e.g., **在留カード required**)
   - Important deadlines (e.g., **Must apply within 30 days**)
   - Key fees or costs
   - Office locations or contact info
4. **Organize related information** - use bullet lists for non-sequential items
5. **Add context when helpful** - mention Japanese terms in parentheses
7. **Acknowledge uncertainty** - if information is incomplete or may vary

Focus on accuracy and practical guidance for people navigating Japanese administrative processes."""

def create_vertex_search_tool() -> VertexAISearchSummaryTool:
    """Create and configure the Vertex AI Search Summary Tool."""
    return VertexAISearchSummaryTool(
        project_id=Config.GOOGLE_CLOUD_PROJECT,
        data_store_id=Config.VERTEX_AI_SEARCH_DATA_STORE_ID,
        location_id='global',
        engine_data_type=0, # Unstructured data source
        # Use same config as regular tool for consistency
        summary_result_count=5,
        summary_include_citations=True,
        
        # Extractive segments (not answers)
        get_extractive_answers=False, # https://cloud.google.com/generative-ai-app-builder/docs/snippets
        max_extractive_segment_count=3,
        return_extractive_segment_score=True,
        num_previous_segments=1,
        num_next_segments=1,
        
        # Safety filters
        summary_spec_kwargs={
            "language_code": "en",
            "ignore_adversarial_query": True,
            "ignore_jail_breaking_query": True,
            "ignore_low_relevant_content": True,
            "use_semantic_chunks": True,
        },

        summary_prompt=SUMMARY_PROMPT,
        name="Japan Procedures Search",
        description="Search for information about official procedures in Japan"
    )


# Create a raw response tool for extracting citations
class VertexAISearchRawTool(VertexAISearchSummaryTool):
    """Extended tool that returns the raw search response for citation extraction."""
    
    def _run(self, query: str) -> Any:
        """Get raw search response with full metadata."""
        request = self._create_search_request(query)
        response = self._client.search(request)
        return response


def create_raw_search_tool() -> VertexAISearchRawTool:
    """Create tool that returns raw response for citation extraction."""
    return VertexAISearchRawTool(
        project_id=Config.GOOGLE_CLOUD_PROJECT,
        data_store_id=Config.VERTEX_AI_SEARCH_DATA_STORE_ID,
        location_id='global',
        engine_data_type=0,
        
        # Use same config as regular tool for consistency
        summary_result_count=5,
        summary_include_citations=True,
        
        # Extractive segments (not answers)
        get_extractive_answers=False, # https://cloud.google.com/generative-ai-app-builder/docs/snippets
        max_extractive_segment_count=3,
        return_extractive_segment_score=True,
        num_previous_segments=1,
        num_next_segments=1,
        
        # Safety filters
        summary_spec_kwargs={
            "language_code": "en",
            "ignore_adversarial_query": True,
            "ignore_jail_breaking_query": True,
            "ignore_low_relevant_content": True,
            "use_semantic_chunks": True,
        },
        
        summary_prompt=SUMMARY_PROMPT,
        name="Japan Procedures Search (Raw)",
        description="Search for information with full citation metadata"
    )


# Initialize tools once at module level
vertex_search_tool = create_vertex_search_tool()
vertex_search_raw_tool = create_raw_search_tool()

