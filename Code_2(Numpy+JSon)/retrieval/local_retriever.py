"""
Local version-aware retriever for the NumPy+JSON vector store.

Drop-in counterpart to retrieval.retriever.VersionAwareRetriever with the
same search() interface and result format - but backed by the lock-free
LocalVectorStore instead of Qdrant.

Version/date filtering logic is reused unchanged from retrieval.filters:
the Qdrant-style filter dicts it produces are converted to Python
predicates inside the store.
"""

import logging
import re
from typing import List, Dict, Any, Optional

from .filters import (
    build_default_filter, build_as_of_filter, build_explicit_version_filter,
    build_compare_filter, detect_query_mode, build_filter_for_mode,
    extract_date_from_question, extract_version_from_question
)
from .vector_store import LocalVectorStore
from .local_embedder import LocalEmbedder

logger = logging.getLogger(__name__)


def _normalize_version(version: str) -> str:
    """
    Ensure a version string carries the 'v' prefix used in the manifest.

    detect_query_mode/extract_version_from_question return bare numbers
    (e.g. '2.0') while stored metadata uses 'v2.0' - normalize the former
    so filters match.
    """
    return version if version.lower().startswith('v') else f"v{version}"


# Compare-style queries ("compare v1.0 and v3.0", "difference between v2 and v3",
# "what changed between ..."). detect_query_mode's version patterns fire on these
# first, so we re-check for a compare intent when it returns explicit_version.
_COMPARE_INTENT_RE = re.compile(
    r'\bcompare\b|\bdifference\s+between\b|\bvs\b|\bchanged?\s+between\b', re.I
)
_VERSION_RE = re.compile(r'v?(\d+\.\d+(?:\.\d+)?)', re.I)


def _detect_mode_with_compare(query_text: str):
    """detect_query_mode, but compare intent is checked before version extraction."""
    mode, params = detect_query_mode(query_text)
    if mode == 'explicit_version' and _COMPARE_INTENT_RE.search(query_text):
        versions = _VERSION_RE.findall(query_text)
        if len(versions) >= 2:
            return 'compare', {
                'version_a': _normalize_version(versions[0]),
                'version_b': _normalize_version(versions[1]),
            }
    return mode, params


class VersionAwareLocalRetriever:
    """Version-aware document search over the local NumPy+JSON store."""

    def __init__(
        self,
        collection_name: str = "version_aware_rag",  # kept for API compatibility
        store_dir: str = "./vector_store",
        embedder: Optional[LocalEmbedder] = None
    ):
        """
        Initialize the retriever.

        Args:
            collection_name: Unused; accepted for API compatibility
            store_dir: Directory holding chunks.json and embeddings.npy
            embedder: LocalEmbedder instance (if None, creates default)
        """
        self.store = LocalVectorStore(store_dir=store_dir)
        self.embedder = embedder or LocalEmbedder()
        logger.info(
            f"Local retriever ready: {self.store.count()} chunks "
            f"from {store_dir}"
        )

    def search(
        self,
        query_text: str,
        limit: int = 10,
        score_threshold: float = 0.3,
        query_mode: Optional[str] = None,
        query_params: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks with version/date filtering.

        Note on score_threshold: all-MiniLM-L6-v2 cosine similarity between a
        natural-language question and a policy chunk typically lands at
        0.45-0.71 for relevant hits. The old 0.7 default silently discarded
        almost every relevant result; 0.3 keeps genuine matches while still
        filtering noise.

        Args:
            query_text: Text to search for
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score (0-1)
            query_mode: 'default', 'as_of', 'explicit_version', 'compare',
                        or None to auto-detect from the query text
            query_params: Parameters for the query mode
            doc_id: Document ID (required for some modes)

        Returns:
            List of results: {'id', 'text', 'score', 'metadata',
                              'query_mode', 'query_params'}
        """
        # Auto-detect query mode if not provided
        if query_mode is None:
            query_mode, query_params = _detect_mode_with_compare(query_text)
            logger.info(f"Auto-detected query mode: {query_mode} with params: {query_params}")

        # Normalize auto-detected versions to the 'vX.Y' form used in metadata
        if query_params:
            for key in ('version', 'version_a', 'version_b'):
                if key in query_params and query_params[key]:
                    query_params[key] = _normalize_version(query_params[key])

        query_embedding = self.embedder.embed_text(query_text)

        if query_mode == 'compare':
            return self._search_compare_mode(
                query_embedding, limit, score_threshold, query_params or {}, doc_id
            )

        qdrant_filter = build_filter_for_mode(query_mode, query_params or {}, doc_id)

        results = self.store.search(
            query_embedding=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            filter_dict=qdrant_filter,
        )

        for result in results:
            result['query_mode'] = query_mode
            result['query_params'] = query_params or {}

        logger.info(f"Found {len(results)} results for query: '{query_text[:50]}...'")
        return results

    def _search_compare_mode(
        self,
        query_embedding: List[float],
        limit: int,
        score_threshold: float,
        params: Dict[str, Any],
        doc_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Handle compare mode: search two versions separately, merge results.

        Args:
            query_embedding: Embedding of the query text
            limit: Maximum results per version (and total)
            score_threshold: Minimum similarity score
            params: Contains 'version_a' and 'version_b'
            doc_id: Document identifier

        Returns:
            Combined results from both versions, sorted by score
        """
        if not doc_id or 'version_a' not in params or 'version_b' not in params:
            logger.error("Missing parameters for compare mode (need doc_id, version_a, version_b)")
            return []

        filter_a = build_explicit_version_filter(doc_id, params['version_a'])
        filter_b = build_explicit_version_filter(doc_id, params['version_b'])

        combined = []
        for version, version_filter in (
            (params['version_a'], filter_a),
            (params['version_b'], filter_b),
        ):
            try:
                results = self.store.search(
                    query_embedding=query_embedding,
                    limit=limit,
                    score_threshold=score_threshold,
                    filter_dict=version_filter,
                )
                for result in results:
                    result['query_mode'] = 'compare'
                    result['query_params'] = params
                    result['version'] = version
                combined.extend(results)
            except Exception as e:
                logger.error(f"Error searching for version {version}: {e}")

        combined.sort(key=lambda x: x['score'], reverse=True)
        return combined[:limit]

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
            List of {'id', 'text', 'metadata'} for the version
        """
        filter_dict = build_explicit_version_filter(doc_id, version)
        results = self.store.scroll(filter_dict=filter_dict, limit=limit)
        logger.info(f"Found {len(results)} chunks for {doc_id} v{version}")
        return results

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
            List of {'id', 'text', 'metadata'} for the current version
        """
        filter_dict = {
            "must": [
                {"key": "doc_id", "match": {"value": doc_id}},
                {"key": "is_current", "match": {"value": True}},
            ]
        }
        results = self.store.scroll(filter_dict=filter_dict, limit=limit)
        logger.info(f"Found {len(results)} current-version chunks for {doc_id}")
        return results


# Convenience function (mirrors retrieval.retriever.search_documents)
def search_documents(
    query_text: str,
    store_dir: str = "./vector_store",
    limit: int = 10,
    score_threshold: float = 0.3,
    query_mode: Optional[str] = None,
    query_params: Optional[Dict[str, Any]] = None,
    doc_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to search documents with version awareness.

    Args:
        query_text: Text to search for
        store_dir: Directory holding chunks.json and embeddings.npy
        limit: Maximum number of results
        score_threshold: Minimum similarity score
        query_mode: Query mode (None to auto-detect)
        query_params: Parameters for the query mode
        doc_id: Document ID (required for some modes)

    Returns:
        List of search results
    """
    retriever = VersionAwareLocalRetriever(store_dir=store_dir)
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
    print("Testing VersionAwareLocalRetriever...")

    retriever = VersionAwareLocalRetriever()

    test_questions = [
        "What is the current password policy?",
        "What was the password policy as of 2025-08-01?",
        "Show me the password policy according to v2.0",
        "Compare version v1.0 and v3.0 of the password policy",
    ]

    for question in test_questions:
        results = retriever.search(query_text=question, limit=3)
        print(f"\nQ: {question}")
        print(f"   {len(results)} result(s)")
        for r in results[:2]:
            meta = r['metadata']
            print(f"   - score {r['score']:.3f} | {meta.get('doc_id')} "
                  f"v{meta.get('version')} (current={meta.get('is_current')})")
