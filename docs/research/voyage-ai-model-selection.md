# Voyage AI Embedding Model Selection

**2026-07-27** — this research supports GitHub issue https://github.com/randclem/sitt-rag/issues/2

## Purpose

This document supports selecting a Voyage AI embedding model for a Python MCP server that performs Retrieval-Augmented Generation (RAG) over a small corpus of Wikipedia cryptid-lore articles (roughly 100–300 relatively short English-language articles). The vector store is ChromaDB, run embedded/local. Voyage AI is already fixed as the embeddings provider on "the cheapest available plan" (i.e. standard pay-as-you-go, no subscription tier); this research determines which specific Voyage embedding model to call from the MCP server, based only on Voyage AI's own primary-source documentation.

## Current Voyage AI Embedding Models

Verified live against `docs.voyageai.com` on 2026-07-27. Voyage AI's lineup has moved on since the "voyage-3.5" generation: the current flagship general-purpose family is **voyage-4** (`voyage-4-large`, `voyage-4`, `voyage-4-lite`), alongside a contextualized-chunk variant (`voyage-context-4`) and domain-specific models. `voyage-3.5`, `voyage-3.5-lite`, and `voyage-3-large` are now listed as "previous generation" (legacy, still callable but not the recommended default), and `voyage-2`/`voyage-large-2`/`voyage-01` etc. are marked deprecated.

| Model | Price / 1M tokens | Dimensions (incl. Matryoshka options) | Max context length | Free tier |
|---|---|---|---|---|
| `voyage-4-large` | $0.12 (source: https://docs.voyageai.com/docs/pricing) | 1024 default; 256 / 512 / 1024 / 2048 selectable (source: https://docs.voyageai.com/docs/embeddings) | 32,000 tokens per input (source: https://docs.voyageai.com/docs/embeddings) | Shared pool of 200M free tokens across the voyage-4 family + `voyage-context-4` + `voyage-code-3` (source: https://docs.voyageai.com/docs/pricing) |
| `voyage-4` | $0.06 (source: https://docs.voyageai.com/docs/pricing) | 1024 default; 256 / 512 / 1024 / 2048 selectable (source: https://docs.voyageai.com/docs/embeddings) | 32,000 tokens per input (source: https://docs.voyageai.com/docs/embeddings) | Same shared 200M-token pool (source: https://docs.voyageai.com/docs/pricing) |
| `voyage-4-lite` | $0.02 (source: https://docs.voyageai.com/docs/pricing) | 1024 default; 256 / 512 / 1024 / 2048 selectable (source: https://docs.voyageai.com/docs/embeddings) | 32,000 tokens per input (source: https://docs.voyageai.com/docs/embeddings) | Same shared 200M-token pool (source: https://docs.voyageai.com/docs/pricing) |
| `voyage-context-4` (contextualized chunk embeddings, not a plain single-vector model) | $0.12 (source: https://docs.voyageai.com/docs/pricing) | 1024 default; 256 / 512 / 1024 / 2048 selectable (source: https://docs.voyageai.com/docs/contextualized-chunk-embeddings) | 32,000 tokens per chunk / 120,000 tokens total context window (source: https://docs.voyageai.com/docs/contextualized-chunk-embeddings) | Same shared 200M-token pool (source: https://docs.voyageai.com/docs/pricing) |
| `voyage-code-3` (code domain) | $0.18 (source: https://docs.voyageai.com/docs/pricing) | 1024 default; 256 / 512 / 1024 / 2048 selectable (source: https://docs.voyageai.com/docs/embeddings) | 32,000 tokens per input (source: https://docs.voyageai.com/docs/embeddings) | Same shared 200M-token pool (source: https://docs.voyageai.com/docs/pricing) |
| `voyage-finance-2` (finance domain) | $0.12 (source: https://docs.voyageai.com/docs/pricing) | 1024 fixed (source: https://docs.voyageai.com/docs/embeddings) | 32,000 tokens per input (source: https://docs.voyageai.com/docs/embeddings) | Shared pool of 50M free tokens across `voyage-multilingual-2`, `voyage-finance-2`, `voyage-law-2`, `voyage-code-2` (source: https://docs.voyageai.com/docs/pricing) |
| `voyage-law-2` (legal domain) | $0.12 (source: https://docs.voyageai.com/docs/pricing) | 1024 fixed (source: https://docs.voyageai.com/docs/embeddings) | 16,000 tokens per input (source: https://docs.voyageai.com/docs/embeddings) | Same shared 50M-token pool (source: https://docs.voyageai.com/docs/pricing) |
| `voyage-multilingual-2` | $0.12 (source: https://docs.voyageai.com/docs/pricing) | 1024 fixed (source: https://docs.voyageai.com/docs/embeddings) | 32,000 tokens per input (source: https://docs.voyageai.com/docs/embeddings) | Same shared 50M-token pool (source: https://docs.voyageai.com/docs/pricing) |
| `voyage-code-2` (legacy code model) | $0.12 (source: https://docs.voyageai.com/docs/pricing) | 1536 fixed (source: https://docs.voyageai.com/docs/embeddings) | 16,000 tokens per input (source: https://docs.voyageai.com/docs/embeddings) | Same shared 50M-token pool (source: https://docs.voyageai.com/docs/pricing) |
| `voyage-multimodal-3.5` / `voyage-multimodal-3` | $0.12 / 1M text tokens + $0.60 / 1B pixels (source: https://docs.voyageai.com/docs/pricing) | not applicable to this project (multimodal) | n/a for text-only use | 200M free text tokens + 150B free pixels, shared pool (source: https://docs.voyageai.com/docs/pricing) |
| `voyage-3-large` (previous generation, legacy) | listed as legacy/previous-generation, retained for existing integrations (source: https://docs.voyageai.com/docs/embeddings) | 1024 default; 256 / 512 / 1024 / 2048 selectable (source: https://docs.voyageai.com/docs/embeddings) | 32,000 tokens (source: https://docs.voyageai.com/docs/embeddings) | n/a — not part of the current-generation free pool structure documented above |
| `voyage-3.5` / `voyage-3.5-lite` (previous generation, legacy) | listed as legacy/previous-generation (source: https://docs.voyageai.com/docs/embeddings) | 1024 default; 256 / 512 / 1024 / 2048 selectable (source: https://docs.voyageai.com/docs/embeddings) | 32,000 tokens (source: https://docs.voyageai.com/docs/embeddings) | n/a |
| `voyage-2`, `voyage-large-2`, `voyage-large-2-instruct`, `voyage-01`, `voyage-lite-01`, `voyage-lite-01-instruct`, `voyage-02`, `voyage-lite-02-instruct` | deprecated (source: https://docs.voyageai.com/docs/embeddings) | 1024–1536 depending on model (source: https://docs.voyageai.com/docs/embeddings) | 4,000–16,000 tokens depending on model (source: https://docs.voyageai.com/docs/embeddings) | n/a — deprecated |

Notes on the table:
- Voyage's own docs describe the recommended usage split as: `voyage-4-large` for "the best general-purpose and multilingual retrieval quality," `voyage-4` for a balance of quality/cost, and `voyage-4-lite` "optimized for latency and cost" (source: https://docs.voyageai.com/docs/embeddings).
- All `voyage-4`-family models plus `voyage-3-large`/`voyage-3.5`/`voyage-3.5-lite`/`voyage-code-3` share the same flexible `output_dimension` options: 2048, 1024 (default), 512, 256 — i.e. Matryoshka-style truncatable embeddings (source: https://docs.voyageai.com/docs/embeddings, https://docs.voyageai.com/docs/flexible-dimensions-and-quantization).
- The API also enforces a separate **per-request** total-token cap across a batched list of inputs (distinct from the per-single-input context length above): `voyage-4-lite`/`voyage-3.5-lite` accept up to 1M tokens total per request, `voyage-4`/`voyage-3.5`/`voyage-2` up to 320K tokens total per request, and `voyage-4-large`/`voyage-3-large`/`voyage-code-3`/`voyage-finance-2`/`voyage-law-2` up to 120K tokens total per request (source: https://docs.voyageai.com/reference/embeddings-api). This does not affect single-article embedding since individual Wikipedia articles are far under any of these caps.
- The official marketing page `voyageai.com/pricing` failed to load directly during this research (redirect loop), and search results otherwise point back to `docs.voyageai.com/docs/pricing` as the canonical, current source — no discrepancy was found between what search snippets reported and what the docs page itself states, so `docs.voyageai.com/docs/pricing` is treated as authoritative throughout this report.

## Rate Limits

Source: https://docs.voyageai.com/docs/rate-limits (fetched directly, cross-checked twice for consistency).

Voyage AI rate limits scale with a **usage tier** that is a function of cumulative billed spend on the account (not a subscription plan):

- **Tier 1** — qualifies once a payment method has been added to the account; this is the base/default tier and the numbers below are the Tier 1 figures (source: https://docs.voyageai.com/docs/rate-limits).
- **Tier 2** — qualifies at ≥$100 cumulative paid usage; limits are 2x Tier 1 (source: https://docs.voyageai.com/docs/rate-limits).
- **Tier 3** — qualifies at ≥$1000 cumulative paid usage; limits are 3x Tier 1 (source: https://docs.voyageai.com/docs/rate-limits).

Tier 1 (base) limits per model, both figures in requests/tokens per minute:

| Model | RPM | TPM |
|---|---|---|
| `voyage-4-large`, `voyage-3-large`, `voyage-code-3`, legacy voyage-1/2 series | 2000 | 3,000,000 (source: https://docs.voyageai.com/docs/rate-limits) |
| `voyage-4`, `voyage-3.5` | 2000 | 8,000,000 (source: https://docs.voyageai.com/docs/rate-limits) |
| `voyage-4-lite`, `voyage-3.5-lite` | 2000 | 16,000,000 (source: https://docs.voyageai.com/docs/rate-limits) |
| `voyage-multimodal-3.5`, `voyage-multimodal-3` | 2000 | 2,000,000 (source: https://docs.voyageai.com/docs/rate-limits) |

The docs state limits apply org-wide: "The rate limits above apply to your entire organization" (source: https://docs.voyageai.com/docs/rate-limits), and project-level limits can be set at or below the org limit.

Caveat: the primary `docs.voyageai.com/docs/rate-limits` page, as fetched, defines its base tier starting from "Tier 1 = payment method added" and does not itself document a separate, lower "no payment method" free-trial rate limit (some third-party/secondary sources mention a much lower free-trial rate such as 3 RPM/10K TPM, but that number could not be confirmed on the primary rate-limits page itself during this research, so it is **not** reported here as fact — only the confirmed Tier 1 numbers above should be relied on).

Practical implication for this project: even at the smallest Tier 1 TPM figure (`voyage-4-large` at 3,000,000 TPM), a one-time embed of a ~500K-token corpus finishes in well under a minute, and the 2000 RPM cap is irrelevant at this scale since the corpus can be embedded in a handful of batched requests.

## Batch pricing

Voyage AI's Batch API offers a documented discount: "Our Batch API provides a simple way to process multiple requests efficiently... It offers a 12-hour completion window and a 33% discount compared to our standard endpoints" (source: https://docs.voyageai.com/docs/pricing). This applies uniformly across models/tiers, not to a specific model. For this project, the batch discount is not decision-relevant (see Recommendation) because the entire corpus is expected to land inside the free monthly token allowance regardless of batch vs. standard endpoint use — but it is worth knowing about for future occasional re-embeds if the corpus ever grows past the free allowance.

## Recommendation

**Use `voyage-4`** (Voyage AI's current general-purpose, balanced model) with the default 1024-dimension output.

- Price: $0.06 / 1M tokens (source: https://docs.voyageai.com/docs/pricing)
- Dimensions: 1024 default, with 256/512/2048 available if dimension tuning is ever needed for ChromaDB storage/performance reasons (source: https://docs.voyageai.com/docs/embeddings)
- Max context length: 32,000 tokens per single input — far more than any individual Wikipedia article will need (source: https://docs.voyageai.com/docs/embeddings)
- Rate limits (Tier 1, base): 2000 RPM / 8,000,000 TPM (source: https://docs.voyageai.com/docs/rate-limits)
- Free tier: part of the shared 200M-token free pool covering the whole voyage-4 family (source: https://docs.voyageai.com/docs/pricing)

**The key finding that drives this recommendation:** for this project's actual volume — roughly 100–300 short articles, an estimated 100K–500K total tokens to embed, plus negligible query-time token volume — the cost of *any* voyage-4-family general-purpose model is effectively **$0**. Voyage's 200M-token free allowance covers this corpus more than 400x over, and even repeated full re-embeds of the corpus (say, dozens of times as the Wikipedia source articles change) would still stay inside the free tier. So the classic "cheapest model" framing doesn't actually bind here — `voyage-4-lite` at $0.02/1M and `voyage-4-large` at $0.12/1M cost the exact same amount ($0) as `voyage-4` at $0.06/1M for this workload. The decision therefore comes down to retrieval quality and operational simplicity, not price.

- **Why not `voyage-4-lite`** (the nominally "cheapest" sticker price): since real-world cost is $0 regardless of which voyage-4-family model is chosen at this token volume, picking `voyage-4-lite` purely for its lower list price buys nothing — it only trades away retrieval quality for a savings that doesn't materialize. Voyage's own guidance frames `voyage-4-lite` as optimized for latency- and cost-sensitive high-QPS production workloads (source: https://docs.voyageai.com/docs/embeddings), which doesn't describe a local, low-traffic MCP server doing an occasional bulk embed plus light query traffic.
- **Why not `voyage-4-large`** (the highest-quality, priciest general model): it is also effectively free at this scale, and Voyage documents it as giving "the best general-purpose and multilingual retrieval quality" (source: https://docs.voyageai.com/docs/embeddings), so it is a defensible upgrade if maximum retrieval fidelity is ever wanted. It was not chosen as the primary recommendation because (a) it is Voyage's higher-quality option primarily aimed at large-scale/production or multilingual-heavy retrieval, where marginal quality gains matter more than they will for a small, English-only, topically narrow (cryptid folklore) Wikipedia corpus with short articles and simple factual queries; (b) `voyage-4` is Voyage's own documented "balance" pick for general-purpose use and is expected to perform close to `voyage-4-large` on straightforward encyclopedic English text; and (c) it has a lower Tier-1 TPM ceiling (3M vs. 8M), which is irrelevant here but adds no benefit either. If retrieval quality on early evaluation turns out inadequate with `voyage-4`, switching to `voyage-4-large` is a one-line model-name change with zero incremental dollar cost at this project's scale, since both remain fully inside the shared free-token pool.
- **Why not a domain-specific model** (`voyage-code-3`, `voyage-finance-2`, `voyage-law-2`): the corpus is general English narrative/encyclopedic text about folklore and cryptids — not source code, financial documents, or legal text — so a general-purpose model is the correct family per Voyage's own model-selection guidance (source: https://docs.voyageai.com/docs/embeddings). Domain-specific models are also priced higher ($0.12–$0.18/1M, source: https://docs.voyageai.com/docs/pricing) and share a smaller 50M-token free pool for the non-voyage-4 domain models, with no offsetting benefit for this content type.
- **Why not `voyage-context-4`**: it produces contextualized *chunk* embeddings rather than simple per-document embeddings, aimed at long/structured documents where chunk-to-chunk context matters (source: https://docs.voyageai.com/docs/contextualized-chunk-embeddings). Short, mostly self-contained Wikipedia articles don't need that extra complexity, and it adds integration overhead in ChromaDB (which expects simple flat vectors) for no clear benefit here.
- **Why not a legacy model** (`voyage-3.5`, `voyage-3-large`, `voyage-2`, etc.): these are explicitly documented as previous-generation/deprecated (source: https://docs.voyageai.com/docs/embeddings) and are not part of the current 200M shared free-token pool structure described on the pricing page, so there is no cost or quality reason to start a new project on them.

## References

1. Pricing — https://docs.voyageai.com/docs/pricing
2. Text Embeddings model guide — https://docs.voyageai.com/docs/embeddings
3. Text embedding API reference (per-request token caps) — https://docs.voyageai.com/reference/embeddings-api
4. Rate Limits — https://docs.voyageai.com/docs/rate-limits
5. FAQ — https://docs.voyageai.com/docs/faq
6. Contextualized Chunk Embeddings — https://docs.voyageai.com/docs/contextualized-chunk-embeddings
7. Flexible Dimensions and Quantization — https://docs.voyageai.com/docs/flexible-dimensions-and-quantization
