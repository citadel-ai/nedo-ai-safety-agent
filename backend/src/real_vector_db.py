"""Real vector database implementation using ChromaDB and sentence transformers."""

import logging
import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.models import VectorSearchResult
from src.settings import load_settings

logger = logging.getLogger(__name__)

settings = load_settings()


class RealVectorDB:
    """Real vector database using ChromaDB with sentence transformers."""

    def __init__(
        self,
        collection_name: str = "japan_helpdesk_docs",
        embedding_model: str = settings.embedding_provider,
        persist_directory: str = "./chroma_db",
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model

        # Initialize embedding model
        self._init_embedding_model()

        # Initialize ChromaDB
        self._init_chromadb()

        # Check and log collection status
        self._check_collection_status()

    def _init_embedding_model(self):
        """Initialize the embedding model."""
        embedding_provider = os.getenv(
            "EMBEDDING_PROVIDER", "sentence_transformers"
        ).lower()

        if embedding_provider == "google" and settings.google_api_key:
            # Use Google's text-embedding model
            try:
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/text-embedding-004",
                    google_api_key=settings.google_api_key,
                )
                logger.info("Using Google Generative AI embeddings")
            except Exception as e:
                logger.warning(f"Failed to initialize Google embeddings: {e}")
                self._fallback_to_sentence_transformers()
        else:
            self._fallback_to_sentence_transformers()

    def _fallback_to_sentence_transformers(self):
        """Fallback to sentence transformers."""
        try:
            # Try the newer langchain-huggingface package first
            try:
                from langchain_huggingface import HuggingFaceEmbeddings

                self.embeddings = HuggingFaceEmbeddings(
                    model_name=self.embedding_model_name
                )
                logger.info(f"Using HuggingFaceEmbeddings: {self.embedding_model_name}")
            except ImportError:
                # Fallback to community package
                from langchain_community.embeddings import SentenceTransformerEmbeddings

                self.embeddings = SentenceTransformerEmbeddings(
                    model_name=self.embedding_model_name
                )
                logger.info(
                    f"Using SentenceTransformer embeddings: {self.embedding_model_name}"
                )
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise

    def _init_chromadb(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Create persist directory
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False),
            )

            # Initialize Langchain Chroma wrapper
            self.vectorstore = Chroma(
                client=self.chroma_client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )

            logger.info(f"ChromaDB initialized with collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def _check_collection_status(self):
        """Check and log the current collection status."""
        try:
            collection_count = len(self.vectorstore.get()["ids"])
            if collection_count == 0:
                logger.info(
                    "Vector database is empty. Use ingest_documents.py to add your documents."
                )
            else:
                logger.info(f"Vector database contains {collection_count} documents")
        except Exception as e:
            logger.warning(f"Could not check collection size: {e}")

    async def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search the vector database."""
        try:
            # Perform similarity search
            search_kwargs = {"k": top_k}
            if filter_metadata:
                search_kwargs["filter"] = filter_metadata

            # Use similarity_search_with_score for similarity scores
            results = self.vectorstore.similarity_search_with_score(
                query=query, **search_kwargs
            )

            # Convert to VectorSearchResult format
            vector_results = []
            for doc, score in results:
                # ChromaDB returns distance (lower is better), convert to similarity
                # For cosine distance, similarity = 1 - distance
                # But we need to handle the range properly
                if score <= 1.0:
                    similarity = max(0.0, 1.0 - score)
                else:
                    # For euclidean distance, use inverse relationship
                    similarity = max(0.0, 1.0 / (1.0 + score))

                if similarity >= min_similarity:
                    result = VectorSearchResult(
                        content=doc.page_content,
                        metadata=doc.metadata,
                        similarity_score=similarity,
                        source=doc.metadata.get("source", "unknown"),
                    )
                    vector_results.append(result)

            logger.info(
                f"Vector search returned {len(vector_results)} results for query: {query[:50]}..."
            )
            return vector_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            # Fallback to empty results
            return []

    def add_documents(
        self, documents: list[str], metadatas: list[dict[str, Any]], sources: list[str]
    ) -> None:
        """Add new documents to the vector database."""
        try:
            docs = []
            ids = []

            for i, (content, metadata, source) in enumerate(
                zip(documents, metadatas, sources, strict=False)
            ):
                doc_id = f"custom_doc_{len(self.vectorstore.get()['ids'])}_{i}"

                doc = Document(
                    page_content=content,
                    metadata={**metadata, "source": source, "doc_id": doc_id},
                )
                docs.append(doc)
                ids.append(doc_id)

            self.vectorstore.add_documents(documents=docs, ids=ids)
            logger.info(f"Added {len(docs)} new documents to vector database")

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise

    def get_collection_info(self) -> dict[str, Any]:
        """Get information about the collection."""
        try:
            data = self.vectorstore.get()
            return {
                "collection_name": self.collection_name,
                "document_count": len(data["ids"]),
                "embedding_model": self.embedding_model_name,
                "persist_directory": self.persist_directory,
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {"error": str(e)}


# Global instance
_vector_db_instance: RealVectorDB | None = None


def get_vector_db() -> RealVectorDB:
    """Get or create the global vector database instance."""
    global _vector_db_instance

    if _vector_db_instance is None:
        _vector_db_instance = RealVectorDB()

    return _vector_db_instance


async def real_vector_search(
    query: str, top_k: int = 5, min_similarity: float = 0.2
) -> list[VectorSearchResult]:
    """Perform real vector search using ChromaDB."""
    vector_db = get_vector_db()
    return await vector_db.search(query, top_k, min_similarity)
