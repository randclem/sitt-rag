"""Ingest pipeline: fetch the "List of cryptids" taxonomy and every linked article,
chunk and embed them, and rebuild the `chunks` and `articles` ChromaDB collections.

Diffing/dedup and fetch retry/backoff are deferred to later slices — this always
does a full rebuild.

Usage: python -m sitt_rag.update
"""

from __future__ import annotations

import sys

from sitt_rag.chunking import chunk_article
from sitt_rag.config import CC_BY_SA_LICENSE, WIKIPEDIA_ORIGIN
from sitt_rag.embeddings import EmbeddingError, VoyageEmbedder
from sitt_rag.store import Source, Store
from sitt_rag.wikipedia import WikipediaError, fetch_article, fetch_redirects, fetch_taxonomy


def run(store: Store | None = None, embedder: VoyageEmbedder | None = None) -> None:
    store = store or Store()
    embedder = embedder or VoyageEmbedder()

    print("Fetching taxonomy...")
    taxonomy = fetch_taxonomy()
    print(f"Found {len(taxonomy)} cryptids across categories.")

    store.reset()

    ingested = 0
    skipped = 0
    for ref in taxonomy:
        print(f"[{ref.category}] {ref.name}...", end=" ")
        try:
            article = fetch_article(ref.wikipedia_title)
            aliases = fetch_redirects(ref.wikipedia_title)
        except WikipediaError as exc:
            print(f"SKIPPED ({exc})")
            skipped += 1
            continue

        source = Source(
            title=article.title,
            url=f"{WIKIPEDIA_ORIGIN}/wiki/{article.title.replace(' ', '_')}",
            license=CC_BY_SA_LICENSE,
        )

        chunks = chunk_article(article)
        embeddings = embedder.embed_documents([c.text for c in chunks])
        store.add_chunks(
            cryptid_name=ref.name,
            category=ref.category,
            source=source,
            chunk_texts=[c.text for c in chunks],
            chunk_sections=[c.section for c in chunks],
            chunk_indices=[c.chunk_index for c in chunks],
            embeddings=embeddings,
        )

        full_text = "\n\n".join(
            f"## {section.title}\n\n" + "\n\n".join(section.paragraphs)
            for section in article.sections
        )
        store.add_article(
            cryptid_name=ref.name,
            category=ref.category,
            source=source,
            full_text=full_text,
            aliases=aliases,
        )

        ingested += 1
        print(f"ok ({len(chunks)} chunks)")

    print(f"Done. Ingested {ingested} cryptids, skipped {skipped}.")


def main() -> None:
    try:
        run()
    except EmbeddingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
