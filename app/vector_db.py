"""Vector database implementation for Japan Helpdesk."""

import numpy as np

from app.types import VectorSearchResult

# No sample documents - system starts empty for real testing
SAMPLE_DOCUMENTS = []


def generate_mock_embedding(text: str) -> np.ndarray:
    """Generate mock embedding vector for text."""
    # Simple mock embedding based on text characteristics
    np.random.seed(hash(text) % 2147483647)  # Deterministic but pseudo-random
    embedding = np.random.normal(0, 1, 384)  # 384-dimensional vector

    # Add some semantic meaning based on keywords
    keywords = {
        "visa": [1, 0, 0, 0, 0, 0, 0, 0],
        "housing": [0, 1, 0, 0, 0, 0, 0, 0],
        "health": [0, 0, 1, 0, 0, 0, 0, 0],
        "bank": [0, 0, 0, 1, 0, 0, 0, 0],
        "tax": [0, 0, 0, 0, 1, 0, 0, 0],
        "work": [0, 0, 0, 0, 0, 1, 0, 0],
        "permanent": [0, 0, 0, 0, 0, 0, 1, 0],
        "immigration": [0, 0, 0, 0, 0, 0, 0, 1],
    }

    text_lower = text.lower()
    for keyword, vector in keywords.items():
        if keyword in text_lower:
            embedding[:8] += np.array(vector) * 2.0

    # Normalize
    embedding = embedding / np.linalg.norm(embedding)
    return embedding


def mock_vector_search(
    query: str, top_k: int = 5, min_similarity: float = 0.5
) -> list[VectorSearchResult]:
    """Mock vector database search."""
    query_embedding = generate_mock_embedding(query)

    results = []
    for doc_data in SAMPLE_DOCUMENTS:
        doc_embedding = generate_mock_embedding(doc_data["content"])

        # Calculate cosine similarity
        similarity = np.dot(query_embedding, doc_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
        )

        if similarity >= min_similarity:
            result = VectorSearchResult(
                content=doc_data["content"],
                metadata=doc_data["metadata"],
                similarity_score=float(similarity),
                source=doc_data["source"],
            )
            results.append(result)

    # Sort by similarity score descending
    results.sort(key=lambda x: x.similarity_score, reverse=True)

    return results[:top_k]


def mock_google_search(query: str) -> list[str]:
    """Mock Google search - returns empty results for real testing."""
    # Return empty results to test real functionality
    return []
