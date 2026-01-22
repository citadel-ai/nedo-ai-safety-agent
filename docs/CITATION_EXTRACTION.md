# Citation Extraction from Answer Method

## Problem

The Vertex AI Search `answer_query` method returns citations in a different structure than the search method:

1. **`answer.citations`** - Contains citation objects with `start_index`, `end_index`, and `sources` that have `reference_id` pointers (like "0", "1", "9")
2. **`answer.references`** - Contains the actual document metadata (URI, title, page) stored by index

The `reference_id` in citations points to the **index** in the `answer.references` array where the document metadata lives.

**⚠️ Critical**: References are nested inside the `answer` object (`answer.references`), not at the top level of the response!

### Example Structure

```
answer_response {
  answer {
    citations[0] {
      start_index: 0
      end_index: 152
      sources {
        reference_id: "0"  ← Points to answer.references[0]
      }
    }
    
    references[0] {
      chunk_info {
        document_metadata {
          uri: "gs://bucket/file.pdf"
          title: "Document Title"
          page_identifier: "2"
        }
      }
    }
  }
}
```

## Solution

The `extract_citations_from_answer_response()` function now:

1. **Builds a reference map** - Creates a lookup dictionary mapping `reference_id` → `chunk_info`
2. **Maps citation sources** - For each citation, extracts `reference_id` and looks up the document metadata
3. **Deduplicates by URI** - Multiple citations may reference the same document (different chunks), so we deduplicate by `gs_uri`
4. **Aggregates page numbers** - When the same document appears multiple times, we collect all page numbers into a single citation
5. **Converts URIs** - Transforms `gs://bucket/file.pdf` to public HTTPS URLs

## Key Features

### Deduplication
```python
# Raw response might have 4 citation objects
# But they all reference the same PDF document
# Result: 1 deduplicated citation with aggregated pages

# Before: [Citation 1 (ref 0, page 1), Citation 2 (ref 0, page 2), Citation 3 (ref 1, page 1)]
# After:  [Citation 1 (Document A, pages 1-2), Citation 2 (Document B, page 1)]
```

### Page Aggregation
```python
# Multiple chunks from the same document → single citation with multiple pages
{
  'citation_number': 1,
  'title': 'National Health Insurance Guide',
  'url': 'https://storage.googleapis.com/bucket/file.pdf',
  'pages': [1, 2, 3],  # Aggregated from multiple chunks
  'source_type': 'PDF'
}
```

### Error Handling
- Gracefully handles missing fields
- Continues processing even if some citations fail
- Prints stack traces for debugging

## Usage

### In Node Functions

```python
from backend.utils.citation_extractor import extract_citations_from_answer_response

response = vertex_answer_tool.invoke(query, config=config)
citations = extract_citations_from_answer_response(response)

# Citations are now ready for frontend display
return {
    "answer": response.answer.answer_text,
    "citations": citations  # Deduplicated with proper metadata
}
```

### In Test Scripts

```python
from backend.utils.citation_extractor import (
    extract_citations_from_answer_response,
    format_citation_display
)

response = client.answer_query(request)
citations = extract_citations_from_answer_response(response)

for citation in citations:
    print(format_citation_display(citation))
    # Output: [1] Document Title (PDF, pages 1-3)
```

## Benefits

✅ **Accurate** - Maps reference IDs correctly to document metadata
✅ **Clean** - Deduplicates to show unique documents only
✅ **Complete** - Aggregates all page numbers for each document
✅ **User-friendly** - Converts gs:// URIs to clickable HTTPS URLs
✅ **Robust** - Handles missing fields and errors gracefully

## Testing

Run the test script to see deduplication in action:

```bash
cd /Users/tapatun/nedo-ai-safety-agent-new
source venv/bin/activate
python notebooks/test_vertex_answer.py
```

Look for the "CITATION DEDUPLICATION DEMO" section which shows:
- Raw citation count from API
- Deduplicated citation count
- Aggregated pages per document

## Related Files

- **`backend/utils/citation_extractor.py`** - Main extraction logic
- **`backend/nodes/search_answer.py`** - Uses extraction in answer node
- **`notebooks/test_vertex_answer.py`** - Test script with examples

