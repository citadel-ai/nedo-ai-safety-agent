"""
PDF Ingestion Script for ChromaDB with Vertex AI Embeddings.

This version uses Vertex AI textembedding-gecko instead of Google AI Studio,
so it uses the same credentials as your LLM (GOOGLE_APPLICATION_CREDENTIALS).
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_google_vertexai import VertexAIEmbeddings

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
DOCS_DIR = Path(__file__).parent.parent / "docs_for_rag"
CHROMA_DB_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "japan_helpdesk_docs"

# Embedding configuration
# Using text-multilingual-embedding-002 - specifically designed for cross-lingual tasks
# Supports Japanese, English, and 100+ languages with strong cross-lingual performance
EMBEDDING_MODEL = "text-multilingual-embedding-002"
VERTEX_AI_LOCATION = os.getenv("VERTEX_AI_LOCATION", "asia-northeast1")

# Alternative models (can be set via environment variable):
# - text-embedding-004: Latest, most capable (768 dimensions)
# - text-multilingual-embedding-002: Best for cross-lingual (768 dimensions) ← DEFAULT
# - textembedding-gecko@003: Legacy but stable (768 dimensions)
# - gemini-embedding-001: Good general purpose (2048 dimensions)

# Chunking configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def check_credentials() -> bool:
    """Check if Vertex AI credentials are available."""
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and Path(creds_path).exists():
        logger.info(f"✓ Found credentials: {creds_path}")
        return True

    # Check if using Application Default Credentials (ADC)
    # These are set via: gcloud auth application-default login
    try:
        from google.auth import default

        credentials, project = default()
        if credentials:
            logger.info("✓ Using Application Default Credentials (ADC)")
            if project:
                logger.info(f"✓ Project: {project}")
            return True
    except Exception as e:
        logger.debug(f"ADC check failed: {e}")

    logger.warning("⚠ No credentials found")
    logger.info("Run: gcloud auth application-default login")
    logger.info("Or set GOOGLE_APPLICATION_CREDENTIALS in .env.local")
    return False


def find_all_pdfs(docs_dir: Path) -> list[Path]:
    """Find all PDF files in docs_for_rag directory."""
    pdf_files = list(docs_dir.rglob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files in {docs_dir}")
    return pdf_files


def extract_category_from_path(pdf_path: Path, docs_dir: Path) -> str:
    """Extract category from file path."""
    relative_path = pdf_path.relative_to(docs_dir)
    if len(relative_path.parts) > 1:
        return relative_path.parts[0]
    return "general"


async def load_and_chunk_pdf(pdf_path: Path, docs_dir: Path) -> list[Any]:
    """Load a PDF and split it into chunks."""
    try:
        logger.info(f"Loading: {pdf_path.name}")

        # Load PDF
        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()

        if not documents:
            logger.warning(f"No content extracted from {pdf_path.name}")
            return []

        # Extract category for metadata
        category = extract_category_from_path(pdf_path, docs_dir)

        # Add metadata
        for doc in documents:
            doc.metadata.update(
                {
                    "source": str(pdf_path.relative_to(docs_dir.parent)),
                    "category": category,
                    "filename": pdf_path.name,
                }
            )

        # Split into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        chunks = text_splitter.split_documents(documents)
        logger.info(f"  → Created {len(chunks)} chunks")

        return chunks

    except Exception as e:
        logger.error(f"Error processing {pdf_path.name}: {e}")
        return []


async def ingest_pdfs():
    """Main ingestion function."""
    logger.info("=" * 60)
    logger.info("PDF Ingestion Script (Vertex AI)")
    logger.info("=" * 60)

    # Check credentials
    if not check_credentials():
        logger.error("Please set up Vertex AI credentials first!")
        return

    # Find all PDFs
    pdf_files = find_all_pdfs(DOCS_DIR)
    if not pdf_files:
        logger.error(f"No PDF files found in {DOCS_DIR}")
        return

    # Process all PDFs
    logger.info(f"\nProcessing {len(pdf_files)} PDF files...")
    all_chunks = []

    for pdf_path in pdf_files:
        chunks = await load_and_chunk_pdf(pdf_path, DOCS_DIR)
        all_chunks.extend(chunks)

    if not all_chunks:
        logger.error("No chunks created from PDFs")
        return

    logger.info(f"\n✓ Total chunks created: {len(all_chunks)}")

    # Initialize Vertex AI embeddings
    logger.info(f"\nInitializing Vertex AI embeddings ({EMBEDDING_MODEL})...")
    logger.info(f"Location: {VERTEX_AI_LOCATION}")

    embeddings = VertexAIEmbeddings(
        model_name=EMBEDDING_MODEL,
        location=VERTEX_AI_LOCATION,
    )

    # Create or update ChromaDB
    logger.info(f"\nCreating ChromaDB at {CHROMA_DB_DIR}...")

    # Remove existing DB if it exists
    if CHROMA_DB_DIR.exists():
        logger.info("  Removing existing ChromaDB...")
        import shutil

        shutil.rmtree(CHROMA_DB_DIR)

    # Create new ChromaDB with all chunks
    logger.info("  Embedding and storing chunks (this may take a while)...")
    logger.info(f"  Processing {len(all_chunks)} chunks...")

    # Process in smaller batches to avoid token limits
    # text-multilingual-embedding-002 has a 20k token input limit
    batch_size = 25  # Reduced from 100 to stay under token limits
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_chunks) - 1) // batch_size + 1
        logger.info(f"  Batch {batch_num}/{total_batches}: {len(batch)} chunks")

        if i == 0:
            # Create on first batch
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                collection_name=COLLECTION_NAME,
                persist_directory=str(CHROMA_DB_DIR),
            )
        else:
            # Add to existing on subsequent batches
            vectorstore.add_documents(batch)

    logger.info("\n" + "=" * 60)
    logger.info("✓ Ingestion Complete!")
    logger.info("=" * 60)
    logger.info(f"Total documents: {len(all_chunks)}")
    logger.info(f"ChromaDB location: {CHROMA_DB_DIR}")
    logger.info(f"Collection name: {COLLECTION_NAME}")
    logger.info(f"Embedding model: {EMBEDDING_MODEL}")
    logger.info(f"Location: {VERTEX_AI_LOCATION}")

    # Show category breakdown
    categories = {}
    for chunk in all_chunks:
        cat = chunk.metadata.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    logger.info("\nChunks by category:")
    for cat, count in sorted(categories.items()):
        logger.info(f"  {cat}: {count} chunks")

    return vectorstore


if __name__ == "__main__":
    asyncio.run(ingest_pdfs())
