"""Voyage AI embeddings client wrapper."""

from __future__ import annotations

import voyageai

from sitt_rag.config import VOYAGE_API_KEY, VOYAGE_MODEL


class EmbeddingError(Exception):
    pass


class VoyageEmbedder:
    def __init__(self, api_key: str | None = VOYAGE_API_KEY, model: str = VOYAGE_MODEL):
        if not api_key:
            raise EmbeddingError(
                "VOYAGE_API_KEY is not set — add it to .env (see .env.example) before ingesting or searching."
            )
        self._client = voyageai.Client(api_key=api_key)
        self._model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        result = self._client.embed(texts, model=self._model, input_type="document")
        return result.embeddings

    def embed_query(self, text: str) -> list[float]:
        result = self._client.embed([text], model=self._model, input_type="query")
        return result.embeddings[0]
