# `get_cryptid` article length vs. single-response token budget

Research for issue #9 (part of #1). Question: `get_cryptid(name)` returns the full
rejoined Wikipedia article text for a cryptid (#4, #5) as a single MCP tool response.
Is that safe given real article sizes on the "List of cryptids" page, or does it need
pagination/truncation?

Method: fetched real article HTML directly from Wikipedia's REST API HTML endpoint
(`https://en.wikipedia.org/api/rest_v1/page/html/{title}`) — the same fetch mechanism
#5 already specifies for ingestion — for 31 cryptids drawn from
[List of cryptids](https://en.wikipedia.org/wiki/List_of_cryptids) (~22% of the ~138
entries on that page). The sample deliberately includes the cryptids expected to have
the longest articles (Bigfoot, Loch Ness Monster, Yeti, Chupacabra, Jersey Devil,
Mothman) alongside a spread of obscure short entries (Anguila peluda, Amomongo,
Mbielu-mbielu-mbielu, Igopogo, Iemisch, Beast of Busco, etc.) and mid-length ones
(Ogopogo, Mokele-mbembe, Fouke Monster, Yowie, Champ, and several US/UK local
cryptids). For each article, "See also" / "References" / "External links" / "Further
reading" / "Notes" / "Sources" / "Bibliography" / "Citations" sections were cut (per
#5's content-filtering plan), HTML tags and citation markers stripped, and the
remaining lead+body prose word-counted. Token count is estimated at the standard
~0.75 words/token rule of thumb (i.e. words × 1.33) — no exact BPE tokenizer was run;
this is an order-of-magnitude estimate, which is what the question calls for.

Raw fetch results (word counts and token estimates), sorted by size:

| Cryptid | Words | Tokens (est.) |
|---|---:|---:|
| Bigfoot | 10,994 | 14,658 |
| Loch Ness Monster | 8,376 | 11,168 |
| Yeti | 4,763 | 6,350 |
| Jersey Devil | 3,881 | 5,174 |
| Chupacabra | 3,174 | 4,232 |
| Ogopogo | 2,732 | 3,642 |
| Mokele-mbembe | 2,459 | 3,278 |
| Fouke Monster | 2,094 | 2,792 |
| Yowie | 1,965 | 2,620 |
| Champ (folklore) | 1,662 | 2,216 |
| Mothman | 1,634 | 2,178 |
| Nittaewo | 1,435 | 1,913 |
| Storsjöodjuret | 1,432 | 1,909 |
| Lizard Man of Scape Ore Swamp | 1,337 | 1,782 |
| Skunk ape | 1,309 | 1,745 |
| Labynkyr Devil | 1,308 | 1,744 |
| Manipogo | 1,294 | 1,725 |
| Flatwoods monster | 1,243 | 1,657 |
| Michigan Dogman | 1,004 | 1,338 |
| Honey Island Swamp monster | 991 | 1,321 |
| Bukit Timah Monkey Man | 928 | 1,237 |
| Mongolian death worm | 920 | 1,226 |
| Nandi bear | 635 | 846 |
| Grafton monster | 577 | 769 |
| Dover Demon | 522 | 696 |
| Igopogo | 426 | 568 |
| Iemisch | 408 | 544 |
| Beast of Busco | 396 | 528 |
| Mbielu-mbielu-mbielu | 324 | 432 |
| Amomongo | 253 | 337 |
| Anguila peluda | 233 | 310 |

**Distribution summary (n=31):**

- Min: 310 tokens (Anguila peluda)
- Median: 1,744 tokens
- Mean: 2,611 tokens
- 90th percentile: 5,174 tokens
- Max: 14,658 tokens (Bigfoot)
- 24/31 (77%) sampled articles are under 3,000 tokens
- Only 2/31 (Bigfoot, Loch Ness Monster) exceed 10,000 tokens; nothing in the sample
  exceeds ~14,700 tokens

Bigfoot and Loch Ness Monster are outliers by a wide margin — roughly 3–6x the median —
but they were deliberately chosen as the *expected* worst case (most-documented,
most-cited cryptids on English Wikipedia), and a second pass sampling more
"famous-adjacent" entries (Yowie, Champ, Mongolian death worm, Flatwoods monster,
Honey Island Swamp monster, Lizard Man of Scape Ore Swamp, Michigan Dogman, Nandi bear)
found nothing else approaching that range — all landed under 2,700 tokens. This
supports treating ~15,000 tokens as a reasonable worst-case ceiling for this corpus
today, not just an artifact of a small sample.

## What's a reasonable single MCP tool-response budget?

- The MCP spec itself (modelcontextprotocol.io, Tools page, `2026-07-28`) does not set
  a numeric limit on `tools/call` result size. It does describe `resource_link` as an
  explicit escape hatch for large content — a tool "MAY return links to Resources...
  to provide additional context or data" instead of embedding it — which is directly
  relevant as a fallback mechanism if this project ever needs one.
- Anthropic's own tool-use guidance (platform.claude.com,
  `build-with-claude/tool-use/implement-tool-use`) advises designing tool responses to
  "return only high-signal information... Bloated responses waste context and make it
  harder for Claude to extract what matters," without giving a hard number.
- Anthropic's engineering writeup "Writing tools for agents"
  (anthropic.com/engineering/writing-tools-for-agents) gives the concrete number this
  project can anchor to: **"For Claude Code, we restrict tool responses to 25,000
  tokens by default,"** with pagination/truncation recommended above that. This is
  Anthropic's own production default for a widely-used agent, so it's a reasonable
  ceiling to adopt here in the absence of a more specific requirement.

## Recommendation: leave `get_cryptid` as a single full-text return — no pagination needed now

Every sampled article, including the deliberately-chosen worst cases, comes in well
under the 25,000-token reference budget — Bigfoot at ~14,658 tokens is the largest
found, about 59% of that budget, and the typical article (median ~1,744 tokens) is
nowhere close. Building pagination/cursor machinery for `get_cryptid` today would add
API surface and client-side complexity to solve a problem the data doesn't show.

That said, two of 31 sampled articles already use more than half of a 25K-token
budget, and Wikipedia articles are living documents that grow over time — so this
isn't a "never revisit" conclusion. Two lightweight guards are worth carrying into
the update-script work (#6) rather than building pagination now:

1. **Monitor, don't pre-build.** When `articles.full_text` is written at ingest, log
   (or flag in the dry-run summary) any cryptid whose token count exceeds a threshold
   — e.g. ~20,000 tokens (80% of the 25K reference budget) — so a maintainer notices
   if a future article grows into genuinely risky territory, instead of it silently
   becoming a problem.
2. **The escape hatch already exists.** If an article ever does cross a size
   threshold that makes single-response return unsafe, the project doesn't need new
   infrastructure — the `chunks` collection (#5) already holds that same article
   split into ~500-token pieces. `get_cryptid` could special-case an oversized article
   by returning a truncated lead plus a pointer to use `search_cryptid_lore` scoped to
   that cryptid, rather than inventing a bespoke pagination/cursor protocol.

**Bottom line: full-text return is safe given real article sizes today. No pagination
or truncation mechanism needs to be designed or built now.** If it's ever needed, the
`chunks` collection is the natural fallback, not a new pagination API.
