"""Modelo de embeddings multilingüe local para ChromaDB."""
from __future__ import annotations

from typing import Sequence

from sentence_transformers import SentenceTransformer

from .config import EMBEDDING_MODEL

_model_cache: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _model_cache
    if _model_cache is None:
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _model_cache


class MultilingualEmbeddingFunction:
    """Función de embeddings multilingüe compatible con ChromaDB 1.5+."""

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        self.model_name = model_name

    def name(self) -> str:
        return f"sentence_transformers_{self.model_name}"

    def _encode(self, texts: Sequence[str]) -> list[list[float]]:
        model = get_embedding_model()
        embeddings = model.encode(list(texts), show_progress_bar=False, normalize_embeddings=True)
        return embeddings.tolist()

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        return self._encode(input)

    def embed_documents(self, input: Sequence[str]) -> list[list[float]]:
        return self._encode(input)

    def embed_query(self, input: Sequence[str]) -> list[list[float]]:
        return self._encode(input)
