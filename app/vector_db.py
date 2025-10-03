# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Vector database implementation for Japan Helpdesk."""

import numpy as np
import hashlib
from typing import List, Dict, Any
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
        "immigration": [0, 0, 0, 0, 0, 0, 0, 1]
    }
    
    text_lower = text.lower()
    for keyword, vector in keywords.items():
        if keyword in text_lower:
            embedding[:8] += np.array(vector) * 2.0
    
    # Normalize
    embedding = embedding / np.linalg.norm(embedding)
    return embedding

def mock_vector_search(query: str, top_k: int = 5, min_similarity: float = 0.5) -> List[VectorSearchResult]:
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
                source=doc_data["source"]
            )
            results.append(result)
    
    # Sort by similarity score descending
    results.sort(key=lambda x: x.similarity_score, reverse=True)
    
    return results[:top_k]

def mock_google_search(query: str) -> List[str]:
    """Mock Google search - returns empty results for real testing."""
    # Return empty results to test real functionality
    return []
