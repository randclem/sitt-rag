# Something in the Trees RAG

An MCP server exposing Retrieval-Augmented Generation over cryptid lore, sourced from
Wikipedia's [List of cryptids](https://en.wikipedia.org/wiki/List_of_cryptids). See
`base-design.md` and GitHub issue #1 for the full spec.

## Setup

```bash
uv sync
cp .env.example .env   # then set VOYAGE_API_KEY
```

## Ingest

Fetches the full cryptid taxonomy and every linked article, chunks and embeds them via
Voyage AI (`voyage-4`), and rebuilds the local ChromaDB collections under `data/`:

```bash
uv run python -m sitt_rag.update
```

This is a full rebuild on every run — no diffing/dedup yet (deferred to a later slice).

## Run the MCP server

```bash
uv run python -m sitt_rag.server
```

Exposes two tools, both returning errors as `{"error": {"code", "message"}}` rather than
raising:

- `search_cryptid_lore(query, top_k=5)` — semantic search over the `chunks` collection.
  `top_k` is silently clamped to 20; there is no score threshold.
- `get_cryptid(name)` — full article lookup from the `articles` collection. Resolves
  `name` case-insensitively against the canonical title, then against known aliases
  (Wikipedia redirects). Unknown names return a `not_found` error.

## Tests

```bash
uv run pytest
```

Tests mock all network and embedding calls — no `VOYAGE_API_KEY` required.
