"""
Text embedding and vector storage for Version-Aware RAG system.
Uses sentence-transformers for embeddings and Qdrant for vector storage.
"""

import uuid
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Embeddings will not work.")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    print("Warning: qdrant-client not installed. Vector storage will not work.")


@dataclass
class EmbeddedChunk:
    """Represents a chunk with its embedding and metadata."""
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]


class Embedder:
    """Handles text embedding and vector storage operations."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "version_aware_rag"
    ):
        """
        Initialize the embedder.

        Args:
            model_name: Sentence transformers model to use
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            collection_name: Name of the Qdrant collection
        """
        self.model_name = model_name
        self.collection_name = collection_name

        # Initialize embedding model
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            print(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            print(f"Embedding dimension: {self.embedding_dim}")
        else:
            self.model = None
            self.embedding_dim = 384  # Default for all-MiniLM-L6-v2
            print("Warning: Using dummy embedding model (sentence-transformers not available)")

        # Initialize Qdrant client
        if QDRANT_AVAILABLE:
            try:
                self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
                self._ensure_collection_exists()
                print(f"Connected to Qdrant at {qdrant_host}:{qdrant_port}")
            except Exception as e:
                print(f"Warning: Could not connect to Qdrant: {e}")
                print("Vector storage will not work until Qdrant is available")
                self.client = None
        else:
            self.client = None

    def _ensure_collection_exists(self):
        """Ensure the Qdrant collection exists with proper configuration."""
        if not self.client:
            return

        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name not in collection_names:
                # Create collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.embedding_dim,
                        distance=models.Distance.COSINE
                    )
                )
                print(f"Created Qdrant collection: {self.collection_name}")
            else:
                print(f"Using existing Qdrant collection: {self.collection_name}")

        except Exception as e:
            print(f"Error ensuring collection exists: {e}")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a text string.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        if not self.model:
            # Return dummy embedding for testing
            return [0.1] * self.embedding_dim

        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * self.embedding_dim

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[EmbeddedChunk]:
        """
        Generate embeddings for multiple text chunks.

        Args:
            chunks: List of chunk dictionaries with 'text' and metadata

        Returns:
            List of EmbeddedChunk objects
        """
        embedded_chunks = []

        for chunk in chunks:
            # Generate unique ID if not present
            chunk_id = chunk.get('id', str(uuid.uuid4()))

            # Get text to embed
            text = chunk['text']

            # Generate embedding
            embedding = self.embed_text(text)

            # Create embedded chunk
            embedded_chunk = EmbeddedChunk(
                id=chunk_id,
                text=text,
                embedding=embedding,
                metadata=chunk.get('metadata', {})
            )

            embedded_chunks.append(embedded_chunk)

        return embedded_chunks

    def store_embeddings(self, embedded_chunks: List[EmbeddedChunk]) -> bool:
        """
        Store embedded chunks in Qdrant vector database.

        Args:
            embedded_chunks: List of EmbeddedChunk objects to store

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            print("Warning: Qdrant client not available, skipping storage")
            return False

        if not embedded_chunks:
            print("No chunks to store")
            return True

        try:
            # Prepare points for Qdrant
            points = []
            for embedded_chunk in embedded_chunks:
                point = models.PointStruct(
                    id=embedded_chunk.id,
                    vector=embedded_chunk.embedding,
                    payload={
                        'text': embedded_chunk.text,
                        **embedded_chunk.metadata
                    }
                )
                points.append(point)

            # Upload to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            print(f"Stored {len(embedded_chunks)} embeddings in Qdrant")
            return True

        except Exception as e:
            print(f"Error storing embeddings: {e}")
            return False

    def search_similar(
        self,
        query_text: str,
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity.

        Args:
            query_text: Text to search for
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of search results with text, metadata, and scores
        """
        if not self.client:
            print("Warning: Qdrant client not available, returning empty results")
            return []

        # Embed the query
        query_embedding = self.embed_text(query_text)

        try:
            # Search in Qdrant
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )

            # Format results
            results = []
            for scored_point in search_result:
                result = {
                    'id': scored_point.id,
                    'text': scored_point.payload.get('text', ''),
                    'score': scored_point.score,
                    'metadata': {k: v for k, v in scored_point.payload.items() if k != 'text'}
                }
                results.append(result)

            return results

        except Exception as e:
            print(f"Error searching embeddings: {e}")
            return []

    def delete_by_metadata(self, metadata_filter: Dict[str, Any]) -> bool:
        """
        Delete vectors matching metadata filter.

        Args:
            metadata_filter: Dictionary of metadata fields to match

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            print("Warning: Qdrant client not available, skipping deletion")
            return False

        try:
            # Build filter condition
            conditions = []
            for key, value in metadata_filter.items():
                condition = models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value)
                )
                conditions.append(condition)

            if not conditions:
                print("No filter conditions provided")
                return False

            filter_obj = models.Filter(must=conditions)

            # Delete matching points
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=filter_obj)
            )

            print(f"Deleted vectors matching filter: {metadata_filter}")
            return True

        except Exception as e:
            print(f"Error deleting by metadata: {e}")
            return False

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the vector collection.

        Returns:
            Dictionary with collection information
        """
        if not self.client:
            return {"status": "client_not_available"}

        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "status": "ok",
                "collection_name": self.collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


def create_content_hash(text: str) -> str:
    """
    Create a hash of content for change detection.

    Args:
        text: Text to hash

    Returns:
        SHA256 hash as hexadecimal string
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def chunks_have_changed(old_chunks: List[Dict], new_chunks: List[Dict]) -> bool:
    """
    Check if chunks have changed by comparing content hashes.

    Args:
        old_chunks: Previous version of chunks
        new_chunks: New version of chunks

        Returns:
            True if chunks have changed, False otherwise
    """
    if len(old_chunks) != len(new_chunks):
        return True

    # Create hash mapping for old chunks
    old_hashes = {}
    for i, chunk in enumerate(old_chunks):
        chunk_id = chunk.get('id', str(i))
        old_hashes[chunk_id] = create_content_hash(chunk['text'])

    # Compare with new chunks
    for i, chunk in enumerate(new_chunks):
        chunk_id = chunk.get('id', str(i))
        new_hash = create_content_hash(chunk['text'])
        old_hash = old_hashes.get(chunk_id)

        if old_hash is None or old_hash != new_hash:
            return True

    return False


# Example usage and testing
if __name__ == "__main__":
    # Test the embedder
    print("Testing Embedder...")

    embedder = Embedder(
        qdrant_host="localhost",
        qdrant_port=6333,
        collection_name="test_collection"
    )

    # Test embedding
    test_text = "This is a test sentence for embedding."
    embedding = embedder.embed_text(test_text)
    print(f"Generated embedding of length: {len(embedding)}")

    # Test content hash
    hash1 = create_content_hash("Hello world")
    hash2 = create_content_hash("Hello world")
    hash3 = create_content_hash("Hello worlds")
    print(f"Hash consistency: {hash1 == hash2} (should be True)")
    print(f"Hash sensitivity: {hash1 != hash3} (should be True)")

    # Test chunk change detection
    chunks1 = [{"id": "1", "text": "First version"}]
    chunks2 = [{"id": "1", "text": "First version"}]
    chunks3 = [{"id": "1", "text": "Second version"}]

    print(f"Same chunks: {not chunks_have_changed(chunks1, chunks2)} (should be True)")
    print(f"Different chunks: {chunks_have_changed(chunks1, chunks3)} (should be True)")

    print("Embedder test completed.")