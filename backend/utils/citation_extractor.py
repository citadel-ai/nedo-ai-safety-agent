"""
Citation extraction utilities for Vertex AI Search responses.

Extracts document references, titles, URIs, and page numbers from raw search responses.
"""

import logging
import re
from typing import Any, Dict, List
from urllib.parse import quote

logger = logging.getLogger(__name__)


def gs_uri_to_public_url(gs_uri: str) -> str:
    """
    Convert a GCS URI to a public HTTPS URL.

    Args:
        gs_uri: URI in format gs://bucket-name/path/to/file.pdf

    Returns:
        Public HTTPS URL in format https://storage.googleapis.com/bucket-name/path/to/file.pdf
    """
    if not gs_uri or not gs_uri.startswith("gs://"):
        return gs_uri

    # Remove gs:// prefix
    path = gs_uri[5:]  # Remove 'gs://'

    # Split into bucket and object path
    parts = path.split("/", 1)
    if len(parts) == 2:
        bucket, object_path = parts
        # URL encode the object path but not the slashes
        encoded_path = "/".join(quote(part, safe="") for part in object_path.split("/"))
        return f"https://storage.googleapis.com/{bucket}/{encoded_path}"

    return gs_uri


def extract_citations_from_raw_response(raw_response) -> List[Dict[str, Any]]:
    """
    Extract citation information from raw Vertex AI Search response.

    Returns a list of citations with:
    - citation_number: The [1], [2], etc. reference number
    - title: Document title (cleaned)
    - url: Public HTTPS URL (converted from gs://)
    - pages: List of page numbers referenced
    - gs_uri: Original GCS URI (for debugging)

    Args:
        raw_response: Raw response from Vertex AI Search

    Returns:
        List of citation dictionaries
    """
    citations = []

    try:
        # Check if response has summary with metadata
        if not hasattr(raw_response, "summary"):
            return citations

        summary = raw_response.summary
        if not hasattr(summary, "summary_with_metadata"):
            return citations

        metadata = summary.summary_with_metadata
        if not hasattr(metadata, "references"):
            return citations

        # Extract each reference
        for idx, reference in enumerate(metadata.references, 1):
            citation = {
                "citation_number": idx,
                "title": None,
                "url": None,
                "gs_uri": None,
                "pages": [],
                "source_type": None,
            }

            # Get title (clean it up)
            if hasattr(reference, "title") and reference.title:
                citation["title"] = reference.title
            else:
                citation["title"] = f"Document {idx}"

            # Get URI and convert to public URL
            if hasattr(reference, "uri") and reference.uri:
                gs_uri = reference.uri
                citation["gs_uri"] = gs_uri
                citation["url"] = gs_uri_to_public_url(gs_uri)

                # Infer source type from URI
                if gs_uri.endswith(".pdf"):
                    citation["source_type"] = "PDF"
                elif gs_uri.endswith((".doc", ".docx")):
                    citation["source_type"] = "Word Document"
                elif gs_uri.endswith((".xls", ".xlsx")):
                    citation["source_type"] = "Spreadsheet"
                else:
                    citation["source_type"] = "Document"

            # Extract page numbers from chunk contents
            pages = set()
            if hasattr(reference, "chunk_contents"):
                for chunk in reference.chunk_contents:
                    if hasattr(chunk, "page_identifier") and chunk.page_identifier:
                        # Page identifier might be "1", "2", etc.
                        try:
                            page_num = int(chunk.page_identifier)
                            pages.add(page_num)
                        except ValueError:
                            # If it's not a number, just add it as-is
                            pages.add(chunk.page_identifier)

            citation["pages"] = sorted(list(pages))
            citations.append(citation)

    except Exception as e:
        # Log error but don't crash
        logger.error(f"Error extracting citations: {e}", exc_info=True)

    return citations


def format_citation_display(citation: Dict[str, Any]) -> str:
    """
    Format a citation for display.

    Args:
        citation: Citation dictionary from extract_citations_from_raw_response

    Returns:
        Formatted string like "[1] Document Title (PDF, pages 1-3)"
    """
    parts = [f"[{citation['citation_number']}]"]

    if citation["title"]:
        parts.append(citation["title"])

    details = []
    if citation["source_type"]:
        details.append(citation["source_type"])

    if citation["pages"]:
        if len(citation["pages"]) == 1:
            details.append(f"page {citation['pages'][0]}")
        else:
            # Format page ranges
            pages_str = ", ".join(str(p) for p in citation["pages"][:5])
            if len(citation["pages"]) > 5:
                pages_str += ", ..."
            details.append(f"pages {pages_str}")

    if details:
        parts.append(f"({', '.join(details)})")

    return " ".join(parts)


def extract_inline_citation_numbers(text: str) -> List[int]:
    """
    Extract citation numbers from text like [1], [2], [3].

    Args:
        text: Text containing inline citations

    Returns:
        List of citation numbers found
    """
    matches = re.findall(r"\[(\d+)\]", text)
    return sorted(list(set(int(m) for m in matches)))


def extract_citations_from_answer_response(answer_response) -> List[Dict[str, Any]]:
    """
    Extract citation information from Vertex AI Answer method response.

    Answer response structure:
    - answer.answer_text: The generated answer with inline [1], [2] citations
    - answer.citations: List of citation objects with reference_id pointers
    - references: List of actual document metadata (mapped by reference_id)

    The answer.citations contain start_index, end_index, and sources with reference_id.
    The reference_id points to the index in the references array where the actual
    document metadata (uri, title, page) is stored.

    Returns deduplicated list of citations with:
    - citation_number: The [1], [2], etc. reference number
    - title: Document title
    - url: Public HTTPS URL (converted from gs:// if needed)
    - pages: List of page numbers
    - source_type: Type of source

    Args:
        answer_response: AnswerQueryResponse from answer_query method

    Returns:
        List of deduplicated citation dictionaries
    """
    citations = []
    seen_uris = {}  # Track URIs to deduplicate

    try:
        # Check if response has answer with citations
        if not hasattr(answer_response, "answer"):
            return citations

        answer = answer_response.answer
        if not hasattr(answer, "citations") or not answer.citations:
            return citations

        # Build references map for lookup
        # Note: references are in answer.references, not at top level
        references_map = {}
        if hasattr(answer, "references"):
            for ref_idx, reference in enumerate(answer.references):
                if hasattr(reference, "chunk_info"):
                    chunk_info = reference.chunk_info
                    if hasattr(chunk_info, "document_metadata"):
                        references_map[str(ref_idx)] = chunk_info

        # Extract each citation and map to document metadata
        for citation_obj in answer.citations:
            # Get reference_id from sources
            reference_ids = []
            if hasattr(citation_obj, "sources"):
                for source in citation_obj.sources:
                    if hasattr(source, "reference_id"):
                        reference_ids.append(source.reference_id)

            # Map each reference_id to document metadata
            for ref_id in reference_ids:
                if ref_id not in references_map:
                    continue

                chunk_info = references_map[ref_id]
                doc_metadata = chunk_info.document_metadata

                # Get URI
                gs_uri = doc_metadata.uri if hasattr(doc_metadata, "uri") else None
                if not gs_uri:
                    continue

                # Check if we've already seen this URI (deduplicate)
                if gs_uri in seen_uris:
                    # Add page to existing citation if not already there
                    if (
                        hasattr(doc_metadata, "page_identifier")
                        and doc_metadata.page_identifier
                    ):
                        try:
                            page_num = int(doc_metadata.page_identifier)
                            if page_num not in seen_uris[gs_uri]["pages"]:
                                seen_uris[gs_uri]["pages"].append(page_num)
                                seen_uris[gs_uri]["pages"].sort()
                        except ValueError:
                            pass
                    continue

                # Create new citation
                citation = {
                    "citation_number": len(citations) + 1,  # Sequential numbering
                    "title": doc_metadata.title
                    if hasattr(doc_metadata, "title")
                    else f"Source {len(citations) + 1}",
                    "url": gs_uri_to_public_url(gs_uri),
                    "gs_uri": gs_uri,
                    "pages": [],
                    "source_type": "answer",
                }

                # Infer source type from URI
                if gs_uri.endswith(".pdf"):
                    citation["source_type"] = "PDF"
                elif gs_uri.endswith((".doc", ".docx")):
                    citation["source_type"] = "Word Document"
                elif gs_uri.endswith((".xls", ".xlsx")):
                    citation["source_type"] = "Spreadsheet"
                elif gs_uri.startswith("http"):
                    citation["source_type"] = "Web Page"
                else:
                    citation["source_type"] = "Document"

                # Extract page number
                if (
                    hasattr(doc_metadata, "page_identifier")
                    and doc_metadata.page_identifier
                ):
                    try:
                        page_num = int(doc_metadata.page_identifier)
                        citation["pages"].append(page_num)
                    except ValueError:
                        pass

                citations.append(citation)
                seen_uris[gs_uri] = citation

    except Exception as e:
        # Log error but don't crash
        logger.error(f"Error extracting citations from answer response: {e}", exc_info=True)

    return citations
