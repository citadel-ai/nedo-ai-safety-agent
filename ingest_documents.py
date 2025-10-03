#!/usr/bin/env python3
"""Document ingestion script for Japan Helpdesk vector database."""

import argparse
import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_text_from_file(file_path: Path) -> str:
    """Extract text from various file formats."""
    try:
        if file_path.suffix.lower() == ".txt":
            return file_path.read_text(encoding="utf-8")
        elif file_path.suffix.lower() == ".md":
            return file_path.read_text(encoding="utf-8")
        elif file_path.suffix.lower() == ".pdf":
            try:
                import PyPDF2

                with open(file_path, "rb") as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                logger.warning("PyPDF2 not installed. Install with: pip install PyPDF2")
                return ""
        elif file_path.suffix.lower() in [".docx", ".doc"]:
            try:
                import docx

                doc = docx.Document(file_path)
                return "\n".join([paragraph.text for paragraph in doc.paragraphs])
            except ImportError:
                logger.warning(
                    "python-docx not installed. Install with: pip install python-docx"
                )
                return ""
        else:
            logger.warning(f"Unsupported file format: {file_path.suffix}")
            return ""
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to end at a sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 100 characters
            sentence_end = max(
                text.rfind(".", start, end),
                text.rfind("!", start, end),
                text.rfind("?", start, end),
            )
            if sentence_end > start + chunk_size - 100:
                end = sentence_end + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap
        if start >= len(text):
            break

    return chunks


async def ingest_documents(
    document_paths: List[str], category: str = "user_docs"
) -> None:
    """Ingest documents into the vector database."""
    from app.real_vector_db import get_vector_db

    vector_db = get_vector_db()

    all_documents = []
    all_metadatas = []
    all_sources = []

    for doc_path in document_paths:
        path = Path(doc_path)

        if path.is_file():
            files_to_process = [path]
        elif path.is_dir():
            # Process all supported files in directory
            files_to_process = []
            for ext in ["*.txt", "*.md", "*.pdf", "*.docx", "*.doc"]:
                files_to_process.extend(path.glob(f"**/{ext}"))
        else:
            logger.warning(f"Path not found: {doc_path}")
            continue

        for file_path in files_to_process:
            logger.info(f"Processing: {file_path}")

            # Extract text
            text = extract_text_from_file(file_path)
            if not text.strip():
                logger.warning(f"No text extracted from: {file_path}")
                continue

            # Chunk the text
            chunks = chunk_text(text)
            logger.info(f"Created {len(chunks)} chunks from {file_path}")

            # Create metadata for each chunk
            for i, chunk in enumerate(chunks):
                all_documents.append(chunk)
                all_metadatas.append(
                    {
                        "document_type": "user_document",
                        "category": category,
                        "subcategory": path.stem,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "file_name": file_path.name,
                        "file_extension": file_path.suffix,
                        "file_size": file_path.stat().st_size,
                        "language": "en",  # Could be auto-detected
                        "authority": "user_provided",
                    }
                )
                all_sources.append(str(file_path))

    if all_documents:
        # Add documents to vector database
        vector_db.add_documents(all_documents, all_metadatas, all_sources)
        logger.info(f"Successfully ingested {len(all_documents)} document chunks")

        # Show updated collection info
        info = vector_db.get_collection_info()
        logger.info(
            f"Vector database now contains {info.get('document_count', 0)} total documents"
        )
    else:
        logger.warning("No documents were processed")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest documents into Japan Helpdesk vector database"
    )
    parser.add_argument(
        "documents", nargs="+", help="Paths to documents or directories to ingest"
    )
    parser.add_argument(
        "--category",
        default="user_docs",
        help="Category for the documents (default: user_docs)",
    )
    parser.add_argument("--test-search", help="Test search query after ingestion")

    args = parser.parse_args()

    # Run ingestion
    asyncio.run(ingest_documents(args.documents, args.category))

    # Test search if requested
    if args.test_search:
        from app.real_vector_db import real_vector_search

        async def test_search():
            results = await real_vector_search(args.test_search, top_k=3)
            print(f"\nTest search results for '{args.test_search}':")
            for i, result in enumerate(results, 1):
                print(f"{i}. Score: {result.similarity_score:.3f}")
                print(f"   Source: {result.source}")
                print(f"   Content: {result.content[:200]}...")
                print()

        asyncio.run(test_search())


if __name__ == "__main__":
    main()
