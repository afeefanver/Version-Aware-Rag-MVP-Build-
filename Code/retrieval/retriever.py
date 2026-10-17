"""
Main retriever for Version-Aware RAG system.
Combines vector search with version/date filtering for different query modes.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    print("Warning: qdrant-client not installed. Vector search will not work.")

try:
    from ingest.embedder import Embedder
except ImportError:
    # Fallback for when running as standalone script
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ingest.embedder import Embedder
from .filters import (
    build_default_filter, build_as_of_filter, build_explicit_version_filter,
    build_compare_filter, detect_query_mode, build_filter_for_mode,
    extract_date_from_question, extract_version_from_question
)

logger = logging.getLogger(__name__)


class VersionAwareRetriever:
    """Main retriever for version-aware document search."""

    def __init__(
        self,
        collection_name: str = "version_aware_rag",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        qdrant_path: Optional[str] = None,
        embedder: Optional[Embedder] = None
    ):
        """
        Initialize the retriever.

        Args:
            collection_name: Name of the Qdrant collection
            qdrant_host: Qdrant server host (ignored if qdrant_path is provided)
            qdrant_port: Qdrant port (ignored if qdrant_path is provided)
            qdrant_path: Path to local Qdrant storage (if None, uses server mode)
            embedder: Embedder instance (if None, creates default)
        """
        self.collection_name = collection_name

        if QDRANT_AVAILABLE:
            try:
                if qdrant_path:
                    # Use local storage mode
                    self.client = QdrantClient(path=qdrant_path)
                    logger.info(f"Using Qdrant local storage at: {qdrant_path}")
                else:
                    # Use server mode
                    self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
                    # Test connection
                    self.client.get_collection(collection_name)
                    logger.info(f"Connected to Qdrant collection: {collection_name}")
            except Exception as e:
                logger.warning(f"Could not initialize Qdrant: {e}")
                self.client = None
        else:
            self.client = None

        # Pass qdrant_path to embedder as well
        self.embedder = embedder or Embedder(qdrant_path=qdrant_path)

    def search(
        self,
        query_text: str,
        limit: int = 10,
        score_threshold: float = 0.7,
        query_mode: Optional[str] = None,
        query_params: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks with optional version/date filtering.

        Args:
            query_text: Text to search for
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score (0-1)
            query_mode: Mode of query ('default', 'as_of', 'explicit_version', 'compare', None for auto-detect)
            query_params: Parameters for the query mode
            doc_id: Document ID (required for some modes)

        Returns:
            List of search results with text, metadata, and scores
        """
        if not self.client:
            logger.warning("Qdrant client not available, returning empty results")
            return []

        # Auto-detect query mode if not provided
        if query_mode is None:
            query_mode, query_params = detect_query_mode(query_text)
            logger.info(f"Auto-detected query mode: {query_mode} with params: {query_params}")

        # Generate query embedding
        query_embedding = self.embedder.embed_text(query_text)

        # Build filter based on mode
        qdrant_filter = None
        if query_mode in ['default', 'as_of', 'explicit_version']:
            qdrant_filter = build_filter_for_mode(query_mode, query_params or {}, doc_id)
        elif query_mode == 'compare':
            # For compare mode, we need to search twice and combine results
            return self._search_compare_mode(
                query_text, query_embedding, limit, score_threshold,
                query_params or {}, doc_id
            )

        # Perform search
        try:
            # Search in Qdrant using query_points (for qdrant-client >= 1.0.0)
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=models.Filter(**qdrant_filter) if qdrant_filter else None
            )

            # Format results
            results = []
            for scored_point in search_result.points:
                result = {
                    'id': scored_point.id,
                    'text': scored_point.payload.get('text', ''),
                    'score': scored_point.score,
                    'metadata': {k: v for k, v in scored_point.payload.items() if k != 'text'},
                    'query_mode': query_mode,
                    'query_params': query_params or {}
                }
                results.append(result)

            logger.info(f"Found {len(results)} results for query: '{query_text[:50]}...'")
            return results

        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []

    def _search_compare_mode(
        self,
        query_text: str,
        query_embedding: List[float],
        limit: int,
        score_threshold: float,
        params: Dict[str, Any],
        doc_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Handle compare mode: search for two versions and combine results.

        Args:
            query_text: Original query text
            query_embedding: Embedding of query text
            limit: Maximum results per version
            score_threshold: Minimum similarity score
            params: Contains 'version_a' and 'version_b'
            doc_id: Document identifier

        Returns:
            Combined list of results from both versions
        """
        if not doc_id or 'version_a' not in params or 'version_b' not in params:
            logger.error("Missing parameters for compare mode")
            return []

        version_a = params['version_a']
        version_b = params['version_b']

        # Build filters for each version
        filter_a = build_explicit_version_filter(doc_id, version_a)
        filter_b = build_explicit_version_filter(doc_id, version_b)

        results_a = []
        results_b = []

        # Search for version A
        try:
            search_result_a = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=models.Filter(**filter_a) if filter_a else None
            )

            for scored_point in search_result_a.points:
                result = {
                    'id': scored_point.id,
                    'text': scored_point.payload.get('text', ''),
                    'score': scored_point.score,
                    'metadata': {k: v for k, v in scored_point.payload.items() if k != 'text'},
                    'query_mode': 'compare',
                    'query_params': params,
                    'version': version_a
                }
                results_a.append(result)

        except Exception as e:
            logger.error(f"Error searching for version {version_a}: {e}")

        # Search for version B
        try:
            search_result_b = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=models.Filter(**filter_b) if filter_b else None
            )

            for scored_point in search_result_b.points:
                result = {
                    'id': scored_point.id,
                    'text': scored_point.payload.get('text', ''),
                    'score': scored_point.score,
                    'metadata': {k: v for k, v in scored_point.payload.items() if k != 'text'},
                    'query_mode': 'compare',
                    'query_params': params,
                    'version': version_b
                }
                results_b.append(result)

        except Exception as e:
            logger.error(f"Error searching for version {version_b}: {e}")

        # Combine and sort by score
        combined_results = results_a + results_b
        combined_results.sort(key=lambda x: x['score'], reverse=True)

        # Limit total results
        final_results = combined_results[:limit]

        logger.info(f"Compare mode: found {len(results_a)} results for {version_a}, "
                   f"{len(results_b)} results for {version_b}, returning {len(final_results)} total")

        return final_results

    def get_chunks_by_doc_and_version(
        self,
        doc_id: str,
        version: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific document and version.

        Args:
            doc_id: Document identifier
            version: Version string
            limit: Maximum number of results

        Returns:
            List of chunks for the specified document and version
        """
        if not self.client:
            logger.warning("Qdrant client not available")
            return []

        filter_dict = build_explicit_version_filter(doc_id, version)

        try:
            # Use scroll to get all points matching the filter
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(**filter_dict) if filter_dict else None,
                limit=limit
            )

            points, next_page_offset = scroll_result

            results = []
            for point in points:
                result = {
                    'id': point.id,
                    'text': point.payload.get('text', ''),
                    'metadata': {k: v for k, v in point.payload.items() if k != 'text'}
                }
                results.append(result)

            logger.info(f"Found {len(results)} chunks for {doc_id} v{version}")
            return results

        except Exception as e:
            logger.error(f"Error getting chunks by doc and version: {e}")
            return []

    def get_current_version_chunks(
        self,
        doc_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all chunks for the current version of a document.

        Args:
            doc_id: Document identifier
            limit: Maximum number of results

        Returns:
            List of chunks for the current version
        """
        # First get the current version from registry would be ideal
        # For now, we'll search for chunks where is_current = true
        if not self.client:
            logger.warning("Qdrant client not available")
            return []

        filter_dict = {
            "must": [
                {
                    "key": "doc_id",
                    "match": {"value": doc_id}
                },
                {
                    "key": "is_current",
                    "match": {"value": True}
                }
            ]
        }

        try:
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(**filter_dict) if filter_dict else None,
                limit=limit
            )

            points, next_page_offset = scroll_result

            results = []
            for point in points:
                result = {
                    'id': point.id,
                    'text': point.payload.get('text', ''),
                    'metadata': {k: v for k, v in point.payload.items() if k != 'text'}
                }
                results.append(result)

            logger.info(f"Found {len(results)} current version chunks for {doc_id}")
            return results

        except Exception as e:
            logger.error(f"Error getting current version chunks: {e}")
            return []


# Convenience functions
def search_documents(
    query_text: str,
    collection_name: str = "version_aware_rag",
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
    qdrant_path: Optional[str] = None,
    limit: int = 10,
    score_threshold: float = 0.7,
    query_mode: Optional[str] = None,
    query_params: Optional[Dict[str, Any]] = None,
    doc_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to search documents with version awareness.

    Args:
        query_text: Text to search for
        collection_name: Name of the Qdrant collection
        qdrant_host: Qdrant server host (ignored if qdrant_path is provided)
        qdrant_port: Qdrant port (ignored if qdrant_path is provided)
        qdrant_path: Path to local Qdrant storage (if None, uses server mode)
        limit: Maximum number of results
        score_threshold: Minimum similarity score
        query_mode: Mode of query ('default', 'as_of', 'explicit_version', 'compare', None for auto-detect)
        query_params: Parameters for the query mode
        doc_id: Document ID (required for some modes)

    Returns:
        List of search results
    """
    retriever = VersionAwareRetriever(
        collection_name=collection_name,
        qdrant_host=qdrant_host,
        qdrant_port=qdrant_port,
        qdrant_path=qdrant_path
    )

    return retriever.search(
        query_text=query_text,
        limit=limit,
        score_threshold=score_threshold,
        query_mode=query_mode,
        query_params=query_params,
        doc_id=doc_id
    )


# Example usage and testing
if __name__ == "__main__":
    # Test the retriever
    print("Testing VersionAwareRetriever...")

    retriever = VersionAwareRetriever()

    # Test search (will return empty if Qdrant not available)
    results = retriever.search(
        query_text="password policy requirements",
        limit=5
    )
    print(f"Search results: {len(results)} items")

    # Test query mode detection
    test_questions = [
        "What is the current password policy?",
        "What was the password policy as of 2025-06-01?",
        "Show me the password policy according to v2.0",
        "Compare version v1.0 and v3.0 of the password policy"
    ]

    print("\nTesting query mode detection:")
    for question in test_questions:
        mode, params = detect_query_mode(question)
        print(f"Q: '{question}'")
        print(f"  Mode: {mode}, Params: {params}")