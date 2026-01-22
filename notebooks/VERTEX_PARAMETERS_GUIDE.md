# Vertex AI Search Summary Tool Parameters Guide

Complete reference for all available parameters in `VertexAISearchSummaryTool`.

## 📋 Required Parameters

```python
project_id: str              # Google Cloud project ID
data_store_id: str          # Vertex AI Search data store ID
name: str                   # Tool name (required by LangChain)
description: str            # Tool description (required by LangChain)
```

## 🎯 Basic Configuration

```python
location_id: str = 'global'          # Data store location
engine_data_type: int = 0            # 0 = unstructured, 1 = structured
summary_result_count: int = 5        # Number of results to use for summary (max 10 for docs, 50 for chunks)
```

## 📝 Summary Configuration

```python
summary_include_citations: bool = True    # Include [1], [2] inline citations
use_semantic_chunks: bool = False        # Use semantic chunks for better quality ⭐
```

## 🔍 Extractive Answers

```python
get_extractive_answers: bool = False              # Get direct text excerpts from documents
max_extractive_segment_count: int = 5            # Max number of segments to return
return_extractive_segment_score: bool = False    # Include relevance scores (0-1)
num_previous_segments: int = 0                   # Context segments before match
num_next_segments: int = 0                       # Context segments after match
```

## 🛡️ Safety & Quality Filters

```python
ignore_adversarial_query: bool = False              # Filter adversarial/harmful queries
ignore_jail_breaking_query: bool = False            # Filter prompt injection attempts
ignore_non_summary_seeking_query: bool = False      # Only allow summary-seeking queries
ignore_low_relevant_content: bool = False           # Only use high-relevance results ⭐
```

## 📊 Response Format

```python
response_format: str = "content"    # Options:
                                    # - "content": Returns string (default)
                                    # - "content_and_artifact": Returns dict with metadata ⭐
```

## 🌐 Advanced Options

```python
language_code: str = None           # BCP47 language code (e.g., "en", "ja")
custom_embedding_ratio: float = 0.0  # Blend custom embeddings (beta feature)
```

## 🎯 Recommended Configurations

### 1. Production-Ready (Balanced)

Best for most use cases - good quality with safety.

```python
tool = VertexAISearchSummaryTool(
    project_id=PROJECT_ID,
    data_store_id=DATA_STORE_ID,
    location_id='global',
    engine_data_type=0,
    
    # Quality
    summary_result_count=10,
    use_semantic_chunks=True,
    ignore_low_relevant_content=True,
    
    # Citations
    summary_include_citations=True,
    get_extractive_answers=True,
    max_extractive_segment_count=10,
    return_extractive_segment_score=True,
    num_previous_segments=1,
    num_next_segments=1,
    
    # Safety
    ignore_adversarial_query=True,
    ignore_jail_breaking_query=True,
    
    name="Japan Procedures Search",
    description="Search for information about official procedures in Japan"
)
```

### 2. Maximum Quality (Slower)

For when quality is more important than speed.

```python
tool = VertexAISearchSummaryTool(
    project_id=PROJECT_ID,
    data_store_id=DATA_STORE_ID,
    location_id='global',
    engine_data_type=0,
    
    summary_result_count=10,
    use_semantic_chunks=True,
    ignore_low_relevant_content=True,
    summary_include_citations=True,
    
    get_extractive_answers=True,
    max_extractive_segment_count=15,
    return_extractive_segment_score=True,
    num_previous_segments=2,
    num_next_segments=2,
    
    response_format="content_and_artifact",
    
    name="High Quality Search",
    description="High-quality search with full context"
)
```

### 3. Fast & Simple (Development)

For quick iteration and testing.

```python
tool = VertexAISearchSummaryTool(
    project_id=PROJECT_ID,
    data_store_id=DATA_STORE_ID,
    location_id='global',
    engine_data_type=0,
    summary_result_count=5,
    summary_include_citations=True,
    
    name="Quick Search",
    description="Fast search for development"
)
```

## 📚 Extracting Citations from Response

### Method 1: Parse Inline Citations

```python
import re

result = tool.invoke(query)
citations = re.findall(r'\[(\d+)\]', result)  # Find [1], [2], etc.
```

### Method 2: Access Raw Response (Most Complete)

```python
class VertexAISearchRawTool(VertexAISearchSummaryTool):
    def _run(self, query: str):
        request = self._create_search_request(query)
        response = self._client.search(request)
        return response

tool_raw = VertexAISearchRawTool(...)
raw_response = tool_raw.invoke(query)

# Extract document metadata
for i, result in enumerate(raw_response.results, 1):
    doc = result.document
    data = doc.derived_struct_data
    
    # Get citation info
    title = data.fields['title'].string_value if 'title' in data.fields else None
    link = data.fields['link'].string_value if 'link' in data.fields else None
    source_type = data.fields['source_type'].string_value if 'source_type' in data.fields else None
    
    # Get extractive segments with page numbers
    if 'extractive_segments' in data.fields:
        segments = data.fields['extractive_segments'].list_value
        for segment in segments.values:
            fields = segment.struct_value.fields
            page = fields['pageNumber'].string_value if 'pageNumber' in fields else None
            score = fields['relevanceScore'].number_value if 'relevanceScore' in fields else None
            content = fields['content'].string_value if 'content' in fields else None
```

### Method 3: Use content_and_artifact Format

```python
tool = VertexAISearchSummaryTool(
    ...,
    response_format="content_and_artifact"
)

result = tool.invoke(query)
# result is a dict:
# {
#   'content': "The summary text...",
#   'artifact': {...metadata...}
# }
```

## 🎯 What Each Parameter Does

| Parameter | Impact | When to Use |
|-----------|--------|-------------|
| `use_semantic_chunks` | +Quality, -Speed | Always for production |
| `ignore_low_relevant_content` | +Quality | When precision > recall |
| `get_extractive_answers` | +Citations, +Context | When you need sources |
| `summary_result_count=10` | +Coverage, -Speed | For comprehensive answers |
| `ignore_adversarial_query` | +Safety | Production systems |
| `response_format="content_and_artifact"` | +Metadata | When you need structured data |

## 🧪 Testing Script

Run the comprehensive testing script to see all parameters in action:

```bash
python notebooks/test_vertex_params_comprehensive.py
```

This will:
- Test all parameter combinations
- Extract citation metadata (links, pages, scores)
- Save raw response to JSON
- Provide recommendations for your use case

## 📖 References

- [Vertex AI Search Documentation](https://cloud.google.com/generative-ai-app-builder/docs/search)
- [LangChain Vertex AI Search](https://python.langchain.com/docs/integrations/tools/google_vertex_ai_search)
- Google Cloud Discovery Engine API: `google.cloud.discoveryengine_v1.types.SearchRequest`

