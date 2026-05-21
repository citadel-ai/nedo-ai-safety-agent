"""Citation extraction from Vertex AI Search and Answer responses.

Parses raw protobuf-like response objects to produce a flat list of
citation dicts (number, title, URL, pages, source info).  Handles
deduplication, GCS-to-HTTPS conversion, and source-organisation lookup.
"""

import logging
import re
import unicodedata
from typing import Any
from urllib.parse import quote, unquote

logger = logging.getLogger(__name__)

SOURCE_HOMEPAGE_MAP: dict[str, str] = {
    # Tokyo 23 Wards (verified from tokyo23city-kuchokai.jp)
    "千代田区": "https://www.city.chiyoda.lg.jp/",
    "中央区": "https://www.city.chuo.lg.jp/",
    "港区": "https://www.city.minato.tokyo.jp/",
    "新宿区": "https://www.city.shinjuku.lg.jp/",
    "文京区": "https://www.city.bunkyo.lg.jp/",
    "台東区": "https://www.city.taito.lg.jp/",
    "墨田区": "https://www.city.sumida.lg.jp/",
    "江東区": "https://www.city.koto.lg.jp/",
    "品川区": "https://www.city.shinagawa.tokyo.jp/",
    "目黒区": "https://www.city.meguro.tokyo.jp/",
    "大田区": "https://www.city.ota.tokyo.jp/",
    "世田谷区": "https://www.city.setagaya.lg.jp/",
    "渋谷区": "https://www.city.shibuya.tokyo.jp/",
    "中野区": "https://www.city.tokyo-nakano.lg.jp/",
    "杉並区": "https://www.city.suginami.tokyo.jp/",
    "豊島区": "https://www.city.toshima.lg.jp/",
    "北区": "https://www.city.kita.lg.jp/",
    "荒川区": "https://www.city.arakawa.tokyo.jp/",
    "板橋区": "https://www.city.itabashi.tokyo.jp/",
    "練馬区": "https://www.city.nerima.tokyo.jp/",
    "足立区": "https://www.city.adachi.tokyo.jp/",
    "葛飾区": "https://www.city.katsushika.lg.jp/",
    "江戸川区": "https://www.city.edogawa.tokyo.jp/",
    # Yokohama city + wards (verified from city.yokohama.lg.jp)
    "横浜市": "https://www.city.yokohama.lg.jp/",
    "横浜市鶴見区": "https://www.city.yokohama.lg.jp/tsurumi/",
    "横浜市神奈川区": "https://www.city.yokohama.lg.jp/kanagawa/",
    "横浜市西区": "https://www.city.yokohama.lg.jp/nishi/",
    "横浜市中区": "https://www.city.yokohama.lg.jp/naka/",
    "横浜市南区": "https://www.city.yokohama.lg.jp/minami/",
    "横浜市保土ヶ谷区": "https://www.city.yokohama.lg.jp/hodogaya/",
    "横浜市磯子区": "https://www.city.yokohama.lg.jp/isogo/",
    "横浜市金沢区": "https://www.city.yokohama.lg.jp/kanazawa/",
    "横浜市港北区": "https://www.city.yokohama.lg.jp/kohoku/",
    "横浜市戸塚区": "https://www.city.yokohama.lg.jp/totsuka/",
    "横浜市港南区": "https://www.city.yokohama.lg.jp/konan/",
    "横浜市旭区": "https://www.city.yokohama.lg.jp/asahi/",
    "横浜市緑区": "https://www.city.yokohama.lg.jp/midori/",
    "横浜市瀬谷区": "https://www.city.yokohama.lg.jp/seya/",
    "横浜市栄区": "https://www.city.yokohama.lg.jp/sakae/",
    "横浜市泉区": "https://www.city.yokohama.lg.jp/izumi/",
    "横浜市都筑区": "https://www.city.yokohama.lg.jp/tsuzuki/",
    "横浜市青葉区": "https://www.city.yokohama.lg.jp/aoba/",
    # Ministries (省庁)
    "厚生労働省": "https://www.mhlw.go.jp/",
    "外務省": "https://www.mofa.go.jp/",
    "法務省": "https://www.moj.go.jp/",
}

_SOURCE_FOLDER_PREFIXES = ("データ収集（自治体）", "データ収集（省庁）")


def _nfc(text: str) -> str:
    """Normalize Unicode to NFC (composed form).

    GCS object names from Vertex AI may arrive in NFD (decomposed) form
    where e.g. デ = テ+゙ instead of a single codepoint.  NFC normalization
    ensures reliable comparison against our literal map keys.
    """
    return unicodedata.normalize("NFC", text)


def extract_source_info(gs_uri: str | None) -> tuple[str | None, str | None]:
    """
    Extract the source organization name and homepage URL from a GCS URI.

    The bucket uses a folder convention where the second path segment
    (after the category folder like データ収集（自治体）) is the organization name.

    Returns:
        (source_name, source_homepage) -- both None when the URI doesn't match.
    """
    if not gs_uri:
        return None, None

    # Normalise: handle both gs:// and https://storage.googleapis.com/ forms
    if gs_uri.startswith("gs://"):
        path = gs_uri[5:]  # strip gs://
        parts = path.split("/", 1)
        object_path = _nfc(unquote(parts[1])) if len(parts) == 2 else ""
    elif "storage.googleapis.com/" in gs_uri:
        after_host = gs_uri.split("storage.googleapis.com/", 1)[1]
        parts = after_host.split("/", 1)
        object_path = _nfc(unquote(parts[1])) if len(parts) == 2 else ""
    else:
        return None, None

    segments = object_path.split("/")
    for i, seg in enumerate(segments):
        if seg in _SOURCE_FOLDER_PREFIXES and i + 1 < len(segments):
            source_name = segments[i + 1]
            source_homepage = SOURCE_HOMEPAGE_MAP.get(source_name)
            return source_name, source_homepage

    return None, None


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


def extract_citations_from_raw_response(raw_response) -> list[dict[str, Any]]:
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
                "source_name": None,
                "source_homepage": None,
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

                citation["source_name"], citation["source_homepage"] = extract_source_info(gs_uri)

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


def format_citation_display(citation: dict[str, Any]) -> str:
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


def extract_inline_citation_numbers(text: str) -> list[int]:
    """
    Extract citation numbers from text like [1], [2], [3].

    Args:
        text: Text containing inline citations

    Returns:
        List of citation numbers found
    """
    matches = re.findall(r"\[(\d+)\]", text)
    return sorted(list(set(int(m) for m in matches)))


def extract_citations_from_answer_response(answer_response) -> list[dict[str, Any]]:
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
                    if hasattr(doc_metadata, "page_identifier") and doc_metadata.page_identifier:
                        try:
                            page_num = int(doc_metadata.page_identifier)
                            if page_num not in seen_uris[gs_uri]["pages"]:
                                seen_uris[gs_uri]["pages"].append(page_num)
                                seen_uris[gs_uri]["pages"].sort()
                        except ValueError:
                            pass
                    continue

                # Create new citation
                src_name, src_homepage = extract_source_info(gs_uri)
                citation = {
                    "citation_number": len(citations) + 1,
                    "title": doc_metadata.title
                    if hasattr(doc_metadata, "title")
                    else f"Source {len(citations) + 1}",
                    "url": gs_uri_to_public_url(gs_uri),
                    "gs_uri": gs_uri,
                    "pages": [],
                    "source_type": "answer",
                    "source_name": src_name,
                    "source_homepage": src_homepage,
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
                if hasattr(doc_metadata, "page_identifier") and doc_metadata.page_identifier:
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
