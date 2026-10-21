"""
Qdrant-free embedding wrapper for the local vector store.

Loads the sentence-transformers model once (lazily) and provides both
single-text and batched encoding. Used by the local ingestion script
and the local retriever so neither touches Qdrant at all.
"""

from typing import List

import numpy as np


class LocalEmbedder:
    """Sentence-transformers wrapper with no vector-DB dependencies."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the embedder.

        Args:
            model_name: sentence-transformers model to load
        """
        self.model_name = model_name
        self._model = None  # lazy-loaded on first use

    @property
    def model(self):
        """Load the model on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def embedding_dim(self) -> int:
        """Dimensionality of the embedding space."""
        return self.model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts (batched, much faster
        than one call per text).

        Args:
            texts: Texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        vectors = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return [v.tolist() for v in np.asarray(vectors)]
