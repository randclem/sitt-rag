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

Runs incrementally: the taxonomy is diffed against what's stored, only added/changed
cryptids are refetched and re-embedded, and a `[y/N]` dry-run summary precedes any write.
Pass `--eval` to score retrieval quality straight after the update.

## Run the MCP server

```bash
uv run python -m sitt_rag.server
```

Exposes four tools, all returning errors as `{"error": {"code", "message"}}` rather than
raising:

- `search_cryptid_lore(query, top_k=5)` — semantic search over the `chunks` collection.
  `top_k` is silently clamped to 20; there is no score threshold.
- `get_cryptid(name)` — full article lookup from the `articles` collection. Resolves
  `name` case-insensitively against the canonical title, then against known aliases
  (Wikipedia redirects). Unknown names return a `not_found` error.
- `list_categories()` — the taxonomy categories present in the ingested corpus.
- `list_cryptids(category=None)` — every ingested cryptid as `{name, category}`, optionally
  filtered by category (case-insensitive).

## Retrieval-quality eval

```bash
uv run python -m sitt_rag.eval
```

Scores `search_cryptid_lore` at **Recall@5** against `golden_queries.json`: one mechanical
`"Tell me about <cryptid>"` query per ingested cryptid, plus ten hand-written thematic
queries ("lake monsters of Scotland", "living dinosaurs reported in the Congo"). A query
passes if *any* of its expected cryptids appears in the top 5 — thematic queries have
several valid answers competing for the same handful of slots.

Output is per-query pass/fail, the actual top 5 with scores on each failure, and an
aggregate score. It is purely informational: **the score never affects the exit code**,
and there is no pass/fail threshold.

After an ingest changes which cryptids are stored, refresh the mechanical entries:

```bash
uv run python -m sitt_rag.eval --regenerate   # rewrites the mechanical section only
```

The eval warns when the golden set has drifted from the store, so a stale mechanical
section can't quietly score cryptids that are gone while ignoring newly ingested ones.

## Tests

```bash
uv run pytest
```

Tests mock all network and embedding calls — no `VOYAGE_API_KEY` required.
