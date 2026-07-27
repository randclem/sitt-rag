# Wikipedia content licensing/attribution obligations for the cryptid-lore MCP server

Research for issue #3 (part of #1). Question: when this project's MCP server retrieves
chunks of Wikipedia article text (embedded, stored in ChromaDB, returned in tool
responses to an LLM client), what does Wikipedia's CC BY-SA / GFDL licensing require —
inline attribution, a source link, a license notice, something else?

Sources consulted are all primary: the Wikimedia Foundation Terms of Use, Wikipedia's
own "Reusing Wikipedia content" and "Copyrights" pages, and the CC BY-SA 4.0 legal code
itself.

## 1. What license governs the text, and who sets its terms

Wikipedia article text is dual-licensed under **CC BY-SA 4.0** and the **GNU Free
Documentation License (GFDL)**, unversioned, no invariant sections/cover texts. Some
imported text is CC BY-SA-only (noted in page footers/talk pages), so CC BY-SA 4.0 is
the safer baseline to design for.

- Wikipedia:Copyrights — https://en.wikipedia.org/wiki/Wikipedia:Copyrights
- Wikimedia Foundation Terms of Use, §7 "Licensing of Content" —
  https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use

The Terms of Use are the binding contract between reusers and the Wikimedia Foundation;
"Reusing Wikipedia content" and "Copyrights" are Wikipedia's own explanatory pages that
restate and elaborate the same obligations. The underlying legal terms are the CC BY-SA
4.0 legal code, which is what actually defines "Share," "Adapted Material,"
"Attribution," and "ShareAlike":

- CC BY-SA 4.0 legal code — https://creativecommons.org/licenses/by-sa/4.0/legalcode

## 2. Does CC BY-SA require attribution for excerpts served this way?

**Yes.** CC BY-SA 4.0 §3(a) makes attribution a condition of the license for anyone who
"Shares" the material — and "Share" is defined broadly as providing the material to the
public "by any means or process that requires permission under the Licensed Rights,
such as reproduction, public display, public performance, distribution, dissemination,
communication, or importation" (CC BY-SA 4.0, §1 "Share" definition —
https://creativecommons.org/licenses/by-sa/4.0/legalcode). Returning retrieved excerpt
text in an MCP tool response, which is then read by an LLM client and typically
surfaced to a human user, falls under "communication"/"dissemination" of the material —
there's no exemption in the license for programmatic, non-human-facing, or
intermediary transmission. The obligation attaches to *sharing* the material at all, not
to the size of the excerpt or the audience.

CC BY-SA 4.0 §3(a)(1) requires the person sharing the material to retain/provide (to the
extent reasonably practicable):

- identification of the creator(s)/those designated for attribution, in the manner
  requested,
- a copyright notice,
- a notice referring to the CC BY-SA public license,
- a notice referring to the disclaimer of warranties,
- a URI or hyperlink to the licensed material,
- indication of any modifications made.

(CC BY-SA 4.0 legal code, §3(a)(1) — https://creativecommons.org/licenses/by-sa/4.0/legalcode)

**What form satisfies "identification of the creator(s)" in practice, per Wikipedia's own guidance:**
Both the Wikimedia Foundation Terms of Use (§7) and Wikipedia:Reusing Wikipedia content
spell out that, because Wikipedia articles have many co-authors, any of the following
independently satisfies attribution — you do not need all of them at once:

1. A hyperlink or URL to the article being reused (preferred "where possible") — since
   the article's history page lists all contributors, linking back to the article is
   accepted as attribution to its authors.
2. A hyperlink or URL to an alternative, freely accessible, stable online copy that
   "provides credit to the authors in a manner equivalent to the credit given on the
   [Wikipedia] Project Website."
3. A list of all authors (which may be filtered to exclude very small/irrelevant
   contributions).

Sources:
- Wikimedia Foundation Terms of Use, §7 — https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use
- Wikipedia:Reusing Wikipedia content — https://en.wikipedia.org/wiki/Wikipedia:Reusing_Wikipedia_content
- Wikipedia:Copyrights — https://en.wikipedia.org/wiki/Wikipedia:Copyrights

**Verified conclusion:** yes, a link back to the specific source article page is
explicitly named by Wikipedia's own guidance (option 1 above, tracking directly to CC
BY-SA §3(a)(1)(v)'s "URI or hyperlink... to the extent reasonably practicable") as
sufficient attribution for online reuse. This is not an assumption — it's stated
directly in both the Terms of Use and Reusing Wikipedia Content. The remaining §3(a)(1)
items (copyright notice, license notice, warranty disclaimer notice) are separate,
additional requirements that a hyperlink alone does not satisfy — see §4 below.

## 3. Does ShareAlike apply to storing/serving excerpts via ChromaDB + MCP?

**Likely no, as long as the excerpts are served unmodified (verbatim text chunks) and
the project doesn't publish its own derivative rewrite of the articles.**

ShareAlike (CC BY-SA 4.0 §3(b)) is explicitly scoped to *Adapted Material*: "if You
Share Adapted Material You produce, the following conditions also apply. The Adapter's
License You apply must be a Creative Commons license with the same License Elements..."
(CC BY-SA 4.0, §3(b) — https://creativecommons.org/licenses/by-sa/4.0/legalcode).
ShareAlike is triggered by *producing and sharing* an adaptation — not by merely sharing
unmodified material, however that material is chunked, indexed, or transmitted.

"Adapted Material" is defined as material "derived from or based upon the Licensed
Material" through translation, alteration, arrangement, transformation, or other
modification "in a manner requiring permission" under copyright (CC BY-SA 4.0, §1 —
https://creativecommons.org/licenses/by-sa/4.0/legalcode). Critically, §2(a)(4) of the
license separately clarifies that the licensor authorizes exercising the licensed
rights "in all media and formats whether now known or hereafter created, and to make
technical modifications necessary to do so" — i.e., format/technical changes needed to
store, transmit, or display the material (chunking text into passages, converting to
embeddings for retrieval, serializing into a tool-response JSON payload) are not, by
themselves, the kind of "alteration" that produces Adapted Material and triggers
ShareAlike.

Applying that to this project's architecture:

- **Chunking article text into passages** for retrieval purposes is a technical/
  mechanical operation, not an edit to the wording, and doesn't create Adapted
  Material.
- **Vector embeddings stored in ChromaDB** are a numeric representation used for
  similarity search; the thing actually *Shared* back to the user is still the
  original verbatim text chunk retrieved, not the embedding itself, so the relevant
  question is about what's re-served, not what's computed internally.
- **Serving the verbatim excerpt text in a tool response** is a "Share" (see §2) of the
  original, unmodified material — attribution applies (§4 above), but ShareAlike does
  not, because no adaptation was produced.
- If the project ever has the LLM (or the server) *rewrite, summarize, or otherwise
  transform* the Wikipedia text and then redistributes that transformed text as if it
  were the source content, that transformed output would likely count as Adapted
  Material, and ShareAlike would require licensing the project's own contribution under
  CC BY-SA 4.0 (or later/compatible). That's a different scenario from simply returning
  retrieved excerpts.

None of the primary sources (Terms of Use, Reusing Wikipedia content, Copyrights, CC
BY-SA legal code) discuss automated reuse, APIs, or RAG/LLM-specific scenarios directly
— there is no primary-source carve-out or special rule for "serving to an LLM" versus
"serving to a human." The analysis above is a direct application of the general
Share / Adapted Material / technical-modification definitions to this system's
mechanics, not a quote of Wikipedia guidance written with RAG in mind.

## 4. Minimum practical fields for compliance

Per CC BY-SA 4.0 §3(a)(1), a full-compliance attribution bundle includes more than just
a link. To stay safely within both the letter of §3(a)(1) and Wikipedia's own accepted
attribution practice, each tool response that includes retrieved excerpt text should
carry:

| Field | Why | Source clause |
|---|---|---|
| **Source URL** (the specific Wikipedia article page, ideally with a permalink/oldid if reproducibility matters) | Satisfies the accepted "hyperlink/URL to the article" attribution method; also satisfies §3(a)(1)(v) URI-to-licensed-material requirement | ToU §7 option (a); CC BY-SA §3(a)(1)(v) |
| **Article title** | Identifies which work is being attributed; needed for the URL/title pairing to be meaningful to the LLM/end user | Reusing Wikipedia content |
| **License name + version** ("CC BY-SA 4.0", ideally with a link to the license text) | Satisfies §3(a)(1)(iii) notice referring to the public license; also functions as the copyright notice in practice ("Text available under CC BY-SA 4.0; see Wikipedia contributors") | CC BY-SA §3(a)(1)(ii)-(iii) |
| **Retrieval/last-updated date** (not a license requirement, but good practice) | Wikipedia content changes; a retrieval date helps the LLM/user understand currency of the excerpt | — (project judgment, not from primary sources) |

The "notice of warranty disclaimer" (§3(a)(1)(iv)) is normally satisfied by linking to
the CC BY-SA 4.0 license text itself, which contains the disclaimer — a separate custom
disclaimer string is not necessary as long as the license link is present.

Because attribution can be satisfied by *either* an author list *or* a link back to the
article (per ToU §7 / Reusing Wikipedia content), and article-level author lists are
long, unstable, and impractical to carry in every tool response, **the source-URL
method is clearly the practical choice for this project** — it's explicitly endorsed as
sufficient by the primary sources and is far cheaper to implement than fetching/
filtering/maintaining per-article contributor lists.

## 5. Recommended minimal compliance approach

For every retrieved excerpt returned in an MCP tool response, include a small
attribution block alongside the excerpt text, e.g.:

```json
{
  "text": "<excerpt>",
  "source": {
    "title": "Mothman",
    "url": "https://en.wikipedia.org/wiki/Mothman",
    "license": "CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)",
    "retrieved": "2026-07-27"
  }
}
```

Concretely:

1. **Store `title`, canonical `url`, and (optionally) a `revision`/`oldid` permalink**
   as metadata on every chunk ingested into ChromaDB, alongside the embedding. This
   makes attribution free at query time — no extra lookups needed.
2. **Always include `title`, `url`, and a license string in the tool response**, not
   just in system/server logs. Since the response is consumed by an LLM that may or may
   not surface it to the end user verbatim, put the attribution in a structured field
   the client can render, and consider instructing the MCP tool's description/schema so
   the calling LLM knows to surface it (e.g., "cite the source URL when quoting this
   excerpt").
3. **Do not need per-article author lists.** Point-to-source-URL is sufficient per
   Wikipedia's own guidance; only fall back to an author list if a specific
   article/edition doesn't have a stable public URL (unlikely for this project's
   Wikipedia-only corpus).
4. **Keep excerpts as unmodified verbatim text.** Don't have an LLM step rewrite/
   paraphrase the stored chunks before storage — that keeps the whole pipeline out of
   "Adapted Material" territory and avoids triggering ShareAlike on the project's own
   corpus/derivative outputs. If the project later adds a feature that publishes
   AI-generated summaries *of* the cryptid articles (as opposed to retrieval of
   original text), that content should be separately reviewed, since it may be Adapted
   Material subject to ShareAlike.
5. **Surface the license name once, prominently, in project-level docs** (e.g. a
   README/NOTICE file: "Cryptid article content sourced from Wikipedia, available under
   CC BY-SA 4.0 / GFDL") in addition to the per-excerpt metadata — this covers the
   general "credit the license" spirit of the Terms of Use beyond just the mechanical
   per-response fields.

This is a minimal but primary-source-grounded design: it satisfies CC BY-SA 4.0 §3(a)
attribution via URL + license notice on every excerpt, does not trigger §3(b)
ShareAlike because the pipeline only ever shares unmodified excerpts, and matches the
specific attribution method (link to article) that Wikipedia's own Terms of Use and
Reusing Wikipedia content page identify as sufficient.

## Sources

- Wikimedia Foundation Terms of Use, §7 "Licensing of Content" —
  https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use
- Wikipedia:Reusing Wikipedia content —
  https://en.wikipedia.org/wiki/Wikipedia:Reusing_Wikipedia_content
- Wikipedia:Copyrights — https://en.wikipedia.org/wiki/Wikipedia:Copyrights
- Creative Commons Attribution-ShareAlike 4.0 International, legal code —
  https://creativecommons.org/licenses/by-sa/4.0/legalcode
