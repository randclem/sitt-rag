# Component map

A local-first RAG server over Wikipedia's cryptid taxonomy: a batch `update.py`
pipeline fetches, chunks, and embeds articles into ChromaDB, and a separate
`server.py` process exposes that store to MCP clients as four read-only tools.

```mermaid
flowchart TB
  CLIENT["MCP client<br/>(Claude, etc.)"]

  subgraph ING["INGEST · python -m sitt_rag.update"]
    direction TB
    UPDATE["update.py<br/>run(): diff taxonomy vs. store,<br/>confirm, commit"]
    WIKIMOD["wikipedia.py<br/>fetch_taxonomy / fetch_article /<br/>fetch_redirects"]
    CHUNK["chunking.py<br/>chunk_article()"]
  end

  subgraph SRV["SERVING · python -m sitt_rag.server"]
    direction TB
    SERVER["server.py<br/>search_cryptid_lore · get_cryptid<br/>list_categories · list_cryptids"]
  end

  subgraph SHARED["SHARED"]
    direction TB
    EMBED["embeddings.py<br/>VoyageEmbedder"]
    STORE["store.py<br/>Store"]
    CONFIG["config.py"]
  end

  WIKI[("Wikipedia<br/>REST + Action API")]
  VOYAGE[("Voyage AI<br/>voyage-4")]
  DATA[("ChromaDB · data/<br/>chunks + articles")]

  CLIENT -->|"tool call"| SERVER
  SERVER -->|"embed_query(query)"| EMBED
  SERVER -->|"search / get_article /<br/>list_categories / list_cryptids"| STORE

  UPDATE -->|"fetch taxonomy + articles"| WIKIMOD
  WIKIMOD -->|"GET, retry on 429/5xx"| WIKI
  UPDATE -->|"chunk_article(article)"| CHUNK
  UPDATE -->|"embed_documents(chunks)"| EMBED
  UPDATE -->|"add_chunks / add_article /<br/>delete_cryptid"| STORE

  EMBED -->|"embed()"| VOYAGE
  STORE -->|"persist"| DATA

  CONFIG -.->|"env vars, paths,<br/>chunk budget"| UPDATE
  CONFIG -.->|"env vars, paths"| SERVER

  classDef external fill:#E4E9EF,stroke:#4C5A6B,color:#1B2430,stroke-width:1px;
  classDef ingest fill:#E6EEE1,stroke:#3F6B4F,color:#20261C,stroke-width:1px;
  classDef runtime fill:#F3E7D9,stroke:#8B5E3C,color:#2B2013,stroke-width:1px;
  classDef shared fill:#EEECE1,stroke:#8A8F79,color:#23271A,stroke-width:1px;
  classDef data fill:#D7E4D9,stroke:#2F4A38,color:#152016,stroke-width:1.5px;
  classDef client fill:#F3E7D9,stroke:#8B5E3C,color:#2B2013,stroke-width:1px;

  class CLIENT client;
  class UPDATE,WIKIMOD,CHUNK ingest;
  class SERVER runtime;
  class EMBED,STORE,CONFIG shared;
  class WIKI,VOYAGE external;
  class DATA data;
```

Two independent entry points share the same storage and embedding code:
`update.py` runs offline to rebuild the corpus, while `server.py` runs
long-lived and only ever reads from it. Dashed arrows are configuration, not
data flow.

## Module reference

### Ingest

- **update.py** — Orchestrates a full diff-and-confirm ingest run: added /
  changed / removed / unchanged / failed buckets, then a `[y/N]` commit.
- **wikipedia.py** — Fetches the taxonomy and article HTML, with
  retry/backoff on transient (429/5xx) errors only.
- **chunking.py** — Splits article sections into token-budgeted chunks with
  one paragraph of overlap, via tiktoken.

### Serving

- **server.py** — MCP server exposing four tools, all returning
  `{"error": {...}}` instead of raising.

### Shared

- **embeddings.py** — Thin Voyage AI client wrapper — `embed_documents` for
  ingest, `embed_query` for search.
- **store.py** — ChromaDB access: `chunks` (embedded, searched) and
  `articles` (full text) collections.
- **config.py** — Env vars, data dir, chunk budget, and the Voyage model
  name — read once at import.

## Stack

python 3.11+ · mcp · chromadb · voyageai · tiktoken · requests + bs4

data/ · chroma.sqlite3 + hnsw index
