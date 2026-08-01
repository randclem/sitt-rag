"""MCP server exposing `search_cryptid_lore` over the ingested cryptid-lore corpus."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from sitt_rag.embeddings import EmbeddingError, VoyageEmbedder
from sitt_rag.store import Store

MAX_TOP_K = 20

mcp = MCPServer(name="sitt-rag")

_store: Store | None = None
_embedder: VoyageEmbedder | None = None


def _get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def _get_embedder() -> VoyageEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = VoyageEmbedder()
    return _embedder


def _error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


@mcp.tool()
def search_cryptid_lore(query: str, top_k: int = 5) -> list[dict] | dict:
    """Search cryptid lore chunks by semantic similarity to `query`.

    Returns up to `top_k` (max 20) ranked results as
    {text, cryptid_name, score, source: {title, url, license}}.
    No minimum-score threshold is applied.
    """
    if not query or not query.strip():
        return _error("invalid_argument", "query must be a non-empty string")

    clamped_top_k = max(1, min(top_k, MAX_TOP_K))

    try:
        embedder = _get_embedder()
        query_embedding = embedder.embed_query(query)
    except EmbeddingError as exc:
        return _error("embedding_unavailable", str(exc))
    except Exception as exc:  # Voyage API/network failures
        return _error("embedding_failed", str(exc))

    try:
        results = _get_store().search(query_embedding, clamped_top_k)
    except Exception as exc:
        return _error("search_failed", str(exc))

    return [
        {
            "text": r.text,
            "cryptid_name": r.cryptid_name,
            "score": r.score,
            "source": {"title": r.source.title, "url": r.source.url, "license": r.source.license},
        }
        for r in results
    ]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
