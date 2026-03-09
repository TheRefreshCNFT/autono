"""Embedding engine — generates and searches vector representations.

Uses sentence-transformers with all-MiniLM-L6-v2 by default:
- 80MB model, runs on CPU
- 384-dimensional embeddings
- Fast enough for real-time node creation
- Good semantic similarity for protocol/technical content

The engine stores embeddings as numpy arrays alongside the JSON nodes.
Search is brute-force cosine similarity — at knowledge-graph scale
(hundreds to low thousands of nodes) this is faster than an index.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import numpy as np
import structlog

log = structlog.get_logger()

# Default model — small, fast, good enough
DEFAULT_MODEL = "all-MiniLM-L6-v2"


class EmbeddingEngine:
    """Generate and search embeddings for knowledge nodes.

    Lazy-loads the model on first use so import is instant.
    Embeddings are stored as .npy files in the knowledge store's embeds/ dir.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL,
                 store_path: str | None = None) -> None:
        self._model_name = model_name
        self._model = None  # lazy loaded
        self._dimension: int = 0
        self._store_path = Path(
            store_path or os.path.expanduser("~/.autono/knowledge/embeds")
        )
        self._store_path.mkdir(parents=True, exist_ok=True)

        # In-memory cache: node_id -> embedding vector
        self._cache: dict[str, np.ndarray] = {}
        self._load_cached_embeddings()

    def _ensure_model(self) -> None:
        """Lazy-load the sentence-transformers model."""
        if self._model is not None:
            return
        if self._model is False:  # previously failed to load
            raise ImportError("sentence_transformers not available")

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            log.warning("embedding.no_sentence_transformers",
                        hint="pip install sentence-transformers for embedding support")
            self._model = False  # sentinel: don't retry
            raise

        log.info("embedding.loading_model", model=self._model_name)
        self._model = SentenceTransformer(self._model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()
        log.info("embedding.model_ready",
                 model=self._model_name, dimension=self._dimension)

    def _load_cached_embeddings(self) -> None:
        """Load all saved embeddings into memory cache."""
        if not self._store_path.exists():
            return
        for npy_file in self._store_path.glob("*.npy"):
            node_id = npy_file.stem
            try:
                self._cache[node_id] = np.load(npy_file)
            except Exception:
                log.warning("embedding.load_failed", file=str(npy_file))

        if self._cache:
            log.info("embedding.cache_loaded", count=len(self._cache))

    # -- Core operations --------------------------------------------------

    def embed(self, text: str) -> np.ndarray:
        """Generate embedding vector for a text string."""
        self._ensure_model()
        return self._model.encode(text, convert_to_numpy=True, normalize_embeddings=True)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for multiple texts at once (faster)."""
        self._ensure_model()
        return self._model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True,
            batch_size=32, show_progress_bar=False,
        )

    def embed_and_store(self, node_id: str, text: str) -> str:
        """Generate embedding, save to disk, cache in memory. Returns hash."""
        vector = self.embed(text)
        self._cache[node_id] = vector

        # Save to disk
        npy_path = self._store_path / f"{node_id}.npy"
        np.save(npy_path, vector)

        # Return hash for the node's embedding_hash field
        embedding_hash = hashlib.sha256(vector.tobytes()).hexdigest()[:16]
        return embedding_hash

    def embed_batch_and_store(self, items: list[tuple[str, str]]) -> dict[str, str]:
        """Embed and store multiple (node_id, text) pairs. Returns {node_id: hash}."""
        if not items:
            return {}

        node_ids = [item[0] for item in items]
        texts = [item[1] for item in items]

        vectors = self.embed_batch(texts)

        results = {}
        for i, node_id in enumerate(node_ids):
            vector = vectors[i]
            self._cache[node_id] = vector

            npy_path = self._store_path / f"{node_id}.npy"
            np.save(npy_path, vector)

            results[node_id] = hashlib.sha256(vector.tobytes()).hexdigest()[:16]

        log.info("embedding.batch_stored", count=len(items))
        return results

    # -- Search operations ------------------------------------------------

    def search(self, query: str, top_k: int = 5,
               threshold: float = 0.3,
               filter_ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Semantic search across all cached embeddings.

        Returns list of {node_id, score} sorted by similarity.
        Only returns results above the threshold.

        Args:
            query: The search text
            top_k: Maximum results to return
            threshold: Minimum cosine similarity (0.0-1.0)
            filter_ids: If provided, only search within these node IDs
        """
        if not self._cache:
            return []

        query_vec = self.embed(query)
        return self.search_by_vector(query_vec, top_k, threshold, filter_ids)

    def search_by_vector(self, query_vec: np.ndarray, top_k: int = 5,
                         threshold: float = 0.3,
                         filter_ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Search using a pre-computed vector."""
        if not self._cache:
            return []

        # Build matrix of cached embeddings
        candidates = filter_ids if filter_ids else list(self._cache.keys())
        candidates = [nid for nid in candidates if nid in self._cache]

        if not candidates:
            return []

        # Stack into matrix for vectorized cosine similarity
        matrix = np.stack([self._cache[nid] for nid in candidates])

        # Cosine similarity (vectors are already normalized)
        scores = matrix @ query_vec

        # Filter and sort
        results = []
        for i, node_id in enumerate(candidates):
            score = float(scores[i])
            if score >= threshold:
                results.append({"node_id": node_id, "score": score})

        results.sort(key=lambda r: -r["score"])
        return results[:top_k]

    def similarity(self, node_id_a: str, node_id_b: str) -> float:
        """Compute cosine similarity between two cached node embeddings."""
        if node_id_a not in self._cache or node_id_b not in self._cache:
            return 0.0
        return float(self._cache[node_id_a] @ self._cache[node_id_b])

    # -- Management -------------------------------------------------------

    def delete(self, node_id: str) -> None:
        """Remove an embedding from cache and disk."""
        self._cache.pop(node_id, None)
        npy_path = self._store_path / f"{node_id}.npy"
        if npy_path.exists():
            npy_path.unlink()

    def has_embedding(self, node_id: str) -> bool:
        """Check if a node has a cached embedding."""
        return node_id in self._cache

    def get_vector(self, node_id: str) -> np.ndarray | None:
        """Get the raw embedding vector for a node."""
        return self._cache.get(node_id)

    @property
    def dimension(self) -> int:
        """Embedding dimension (384 for all-MiniLM-L6-v2)."""
        if self._dimension == 0:
            self._ensure_model()
        return self._dimension

    @property
    def cached_count(self) -> int:
        return len(self._cache)

    def stats(self) -> dict[str, Any]:
        return {
            "model": self._model_name,
            "dimension": self._dimension,
            "cached_embeddings": len(self._cache),
            "model_loaded": self._model is not None,
        }
