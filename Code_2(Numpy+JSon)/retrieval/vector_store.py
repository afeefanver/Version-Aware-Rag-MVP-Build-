"""
Local NumPy+JSON vector store for Version-Aware RAG system.

A lightweight, lock-free replacement for Qdrant local storage mode.
Designed for small-to-medium corpora (up to ~100k chunks) where an
exact brute-force cosine search over an in-memory matrix is instant.

Storage layout (two plain files in the store directory):
    chunks.json      list of metadata dicts (doc_id, version, dates, text, ...)
    embeddings.npy   float32 matrix, shape (N, dim); row i <-> chunks.json[i]

Because rows are aligned by position, the row index doubles as the point ID.

Filtering reuses the same Qdrant-style filter dicts produced by
retrieval.filters (must / should / must_not with match, range, is_null),
converted here into plain Python predicates - so no filter logic is duplicated.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Qdrant filter dict -> Python predicate
# ---------------------------------------------------------------------------

def _match_predicate(cond: Dict[str, Any]) -> Callable[[Any], bool]:
    """Build a predicate for a 'match' condition."""
    expected = cond["match"]["value"]

    def pred(value: Any) -> bool:
        return value == expected
    return pred


def _range_predicate(cond: Dict[str, Any]) -> Callable[[Any], bool]:
    """Build a predicate for a 'range' condition (lte/gte on ISO date strings)."""
    bounds = cond["range"]
    lte = bounds.get("lte")
    gte = bounds.get("gte")

    def pred(value: Any) -> bool:
        if value is None:
            return False
        # ISO date strings (YYYY-MM-DD) compare correctly as plain strings
        if lte is not None and not (value <= lte):
            return False
        if gte is not None and not (value >= gte):
            return False
        return True
    return pred


def _is_null_predicate(cond: Dict[str, Any]) -> Callable[[Any], bool]:
    """Build a predicate for an 'is_null' condition."""
    def pred(value: Any) -> bool:
        return value is None
    return pred


def _condition_predicate(cond: Dict[str, Any]) -> Callable[[Any], bool]:
    """Build a predicate for a single condition (match / range / is_null)."""
    if "match" in cond:
        return _match_predicate(cond)
    if "range" in cond:
        return _range_predicate(cond)
    if "is_null" in cond:
        return _is_null_predicate(cond)
    raise ValueError(f"Unsupported filter condition: {cond}")


def _condition_on_key(cond: Dict[str, Any]) -> Callable[[Dict[str, Any]], bool]:
    """Lift a condition predicate onto a metadata dict via its 'key'."""
    key = cond["key"]
    pred = _condition_predicate(cond)

    def pred_on_meta(metadata: Dict[str, Any]) -> bool:
        return pred(metadata.get(key))
    return pred_on_meta


def filter_dict_to_predicate(filter_dict: Optional[Dict[str, Any]]) -> Callable[[Dict[str, Any]], bool]:
    """
    Convert a Qdrant-style filter dict into a Python predicate over metadata.

    Semantics replicated from Qdrant:
        must      -> all conditions must pass (AND)
        should    -> at least one condition must pass (OR), only if present
        must_not  -> no condition may pass (NOT)

    Args:
        filter_dict: Qdrant-compatible filter dictionary (or None for match-all)

    Returns:
        Predicate taking a metadata dict and returning True if it passes
    """
    if not filter_dict:
        return lambda metadata: True

    must = [_condition_on_key(c) for c in filter_dict.get("must", [])]
    should = [_condition_on_key(c) for c in filter_dict.get("should", [])]
    must_not = [_condition_on_key(c) for c in filter_dict.get("must_not", [])]

    def pred(metadata: Dict[str, Any]) -> bool:
        if not all(p(metadata) for p in must):
            return False
        if should and not any(p(metadata) for p in should):
            return False
        if any(p(metadata) for p in must_not):
            return False
        return True
    return pred


# ---------------------------------------------------------------------------
# Local vector store
# ---------------------------------------------------------------------------

class LocalVectorStore:
    """NumPy-backed vector store with JSON metadata and exact cosine search."""

    def __init__(self, store_dir: str = "./vector_store", dim: int = 384):
        """
        Initialize (and load, if present) a local vector store.

        Args:
            store_dir: Directory holding chunks.json and embeddings.npy
            dim: Embedding dimension (default 384 for all-MiniLM-L6-v2)
        """
        self.store_dir = Path(store_dir)
        self.dim = dim
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings = np.zeros((0, dim), dtype=np.float32)

        if (self.store_dir / "chunks.json").exists():
            self.load()

    # -- persistence --------------------------------------------------------

    def save(self) -> None:
        """Write chunks.json and embeddings.npy to the store directory."""
        self.store_dir.mkdir(parents=True, exist_ok=True)

        with open(self.store_dir / "chunks.json", "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, indent=2, ensure_ascii=False)

        np.save(self.store_dir / "embeddings.npy", self.embeddings)

    def load(self) -> None:
        """Load chunks.json and embeddings.npy from the store directory."""
        with open(self.store_dir / "chunks.json", "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        self.embeddings = np.load(self.store_dir / "embeddings.npy").astype(np.float32)

        if len(self.chunks) != self.embeddings.shape[0]:
            raise ValueError(
                f"Store corrupted: {len(self.chunks)} chunks but "
                f"{self.embeddings.shape[0]} embeddings"
            )

    # -- writing ------------------------------------------------------------

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> List[int]:
        """
        Append chunks with their embeddings to the store.

        Args:
            chunks: List of metadata dicts (must include 'text')
            embeddings: Matching list of embedding vectors

        Returns:
            List of row IDs assigned to the new chunks

        Raises:
            ValueError: If chunks and embeddings lengths differ
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must align"
            )

        new_vecs = np.asarray(embeddings, dtype=np.float32)
        if new_vecs.ndim == 1:
            new_vecs = new_vecs.reshape(1, -1)
        if new_vecs.shape[1] != self.dim:
            raise ValueError(
                f"Embedding dim {new_vecs.shape[1]} != store dim {self.dim}"
            )

        # Normalize once at write time so search is a plain dot product
        norms = np.linalg.norm(new_vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0  # guard against zero vectors
        new_vecs = new_vecs / norms

        start_id = self.embeddings.shape[0]
        self.embeddings = np.vstack([self.embeddings, new_vecs]) if start_id else new_vecs
        self.chunks.extend(chunks)

        return list(range(start_id, start_id + len(chunks)))

    # -- searching ----------------------------------------------------------

    def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Exact cosine search with metadata filtering.

        Mirrors Qdrant query_points semantics: filter first, then rank,
        then apply score_threshold, then truncate to limit.

        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            filter_dict: Qdrant-style filter dict (or None for match-all)

        Returns:
            List of {'id', 'text', 'score', 'metadata'} sorted by score desc
        """
        if self.embeddings.shape[0] == 0:
            return []

        query = np.asarray(query_embedding, dtype=np.float32).reshape(-1)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm

        scores = self.embeddings @ query  # cosine similarity (both normalized)

        predicate = filter_dict_to_predicate(filter_dict)
        candidates = [i for i, meta in enumerate(self.chunks) if predicate(meta)]

        candidates.sort(key=lambda i: scores[i], reverse=True)

        results = []
        for i in candidates:
            score = float(scores[i])
            if score < score_threshold:
                break
            results.append({
                'id': i,
                'text': self.chunks[i].get('text', ''),
                'score': score,
                'metadata': {k: v for k, v in self.chunks[i].items() if k != 'text'},
            })
            if len(results) >= limit:
                break

        return results

    def scroll(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return all chunks matching a filter (mirrors Qdrant scroll).

        Args:
            filter_dict: Qdrant-style filter dict (or None for match-all)
            limit: Maximum number of results

        Returns:
            List of {'id', 'text', 'metadata'} (no scores, unordered)
        """
        predicate = filter_dict_to_predicate(filter_dict)
        results = []
        for i, meta in enumerate(self.chunks):
            if predicate(meta):
                results.append({
                    'id': i,
                    'text': meta.get('text', ''),
                    'metadata': {k: v for k, v in meta.items() if k != 'text'},
                })
                if len(results) >= limit:
                    break
        return results

    # -- info ---------------------------------------------------------------

    def count(self) -> int:
        """Number of chunks in the store."""
        return len(self.chunks)

    def info(self) -> Dict[str, Any]:
        """Summary of store contents."""
        versions = sorted({(c.get('doc_id'), c.get('version')) for c in self.chunks})
        return {
            'store_dir': str(self.store_dir),
            'chunks': len(self.chunks),
            'dim': self.dim,
            'doc_versions': [f"{d} {v}" for d, v in versions],
        }
