# Citation Extraction

## Vertex AI Search Answer Response Structure

The `answer_query` method returns citations in two parts:

1. **`answer.citations`** -- citation objects with `start_index`, `end_index`, and `sources` containing `reference_id` pointers (e.g. "0", "1", "9")
2. **`answer.references`** -- the actual document metadata (URI, title, page) indexed by position

The `reference_id` in a citation points to the index in `answer.references` where the document metadata lives.

**Important**: References are nested inside the `answer` object (`answer.references`), not at the top level.

```
answer_response {
  answer {
    citations[0] {
      start_index: 0
      end_index: 152
      sources { reference_id: "0" }  # → answer.references[0]
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

## Extraction Logic

`extract_citations_from_answer_response()` does the following:

1. **Builds a reference map** -- `reference_id` → `chunk_info`
2. **Maps citation sources** -- looks up document metadata for each citation
3. **Deduplicates by URI** -- multiple citations may reference the same document
4. **Aggregates page numbers** -- collects all page numbers into a single citation entry
5. **Converts URIs** -- transforms `gs://` URIs to public HTTPS URLs

### Output Format

```python
{
    'citation_number': 1,
    'title': 'National Health Insurance Guide',
    'url': 'https://storage.googleapis.com/bucket/file.pdf',
    'pages': [1, 2, 3],
    'source_type': 'PDF'
}
```

## Usage

```python
from backend.utils.citation_extractor import extract_citations_from_answer_response

response = vertex_answer_tool.invoke(query, config=config)
citations = extract_citations_from_answer_response(response)
```

## Related Files

- `backend/utils/citation_extractor.py` -- extraction logic
- `backend/nodes/search_answer.py` -- uses extraction in the answer node
