import logging
from typing import List, Union
import numpy as np
from config.config import Config

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Manages sentence-transformers/all-MiniLM-L6-v2 embeddings with batching and fallback."""

    def __init__(self, model_name: str = Config.EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy load model to accelerate startup time."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                # Try loading from local cache first to avoid network timeout in sandbox
                try:
                    self._model = SentenceTransformer(self.model_name, local_files_only=True)
                except Exception:
                    self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(
                    f"Could not load SentenceTransformer ({str(e)}). Falling back to deterministic embedding simulator."
                )
                self._model = "FALLBACK"
        return self._model

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate normalized vector embeddings for a list of texts."""
        if not texts:
            return []

        # Sanitize texts
        cleaned_texts = [t.strip() if t and t.strip() else "empty document" for t in texts]

        if self.model != "FALLBACK":
            try:
                embeddings = self.model.encode(
                    cleaned_texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    normalize_embeddings=True
                )
                return embeddings.tolist()
            except Exception as e:
                logger.error(f"Error during SentenceTransformer encoding: {e}. Using fallback.")

        # Deterministic 384-dimension pseudo-embedding for testing or offline environment
        return [self._deterministic_fallback_embed(t) for t in cleaned_texts]

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding vector for a single query text."""
        results = self.embed_texts([query])
        return results[0] if results else [0.0] * 384

    def _deterministic_fallback_embed(self, text: str, dim: int = 384) -> List[float]:
        """Compute deterministic unit-normalized embedding for offline test environments."""
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Seed pseudo-random generator with hash bytes
        seed = int.from_bytes(h[:4], "little")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(dim)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()
