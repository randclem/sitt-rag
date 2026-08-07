"""Incremental ingest: diff the current "List of cryptids" taxonomy against what's
already stored, fetch only what's added or changed, hard-delete what's gone, and
require a `[y/N]` confirmation before writing anything.

Usage: python -m sitt_rag.update
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass

from sitt_rag.chunking import chunk_article
from sitt_rag.config import CC_BY_SA_LICENSE, WIKIPEDIA_ORIGIN
from sitt_rag.embeddings import EmbeddingError, VoyageEmbedder
from sitt_rag.store import Source, Store
from sitt_rag.wikipedia import Article, CryptidRef, WikipediaError, fetch_article, fetch_redirects, fetch_taxonomy


def full_text_for(article: Article) -> str:
    """Assemble an article's full stored text, section by section."""
    return "\n\n".join(
        f"## {section.title}\n\n" + "\n\n".join(section.paragraphs) for section in article.sections
    )


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class _Fetched:
    ref: CryptidRef
    article: Article
    aliases: list[str]
    full_text: str
    content_hash: str


def _fetch(ref: CryptidRef) -> _Fetched | None:
    """Fetch and hash one cryptid's article. Returns None (and prints) on failure —
    the run continues, leaving any existing stored data for it untouched."""
    try:
        article = fetch_article(ref.wikipedia_title)
        aliases = fetch_redirects(ref.wikipedia_title)
    except WikipediaError as exc:
        print(f"SKIPPED ({ref.name}): {exc}")
        return None
    text = full_text_for(article)
    return _Fetched(ref=ref, article=article, aliases=aliases, full_text=text, content_hash=content_hash(text))


def _insert(store: Store, embedder: VoyageEmbedder, fetched: _Fetched) -> None:
    ref = fetched.ref
    source = Source(
        title=fetched.article.title,
        url=f"{WIKIPEDIA_ORIGIN}/wiki/{fetched.article.title.replace(' ', '_')}",
        license=CC_BY_SA_LICENSE,
    )
    chunks = chunk_article(fetched.article)
    embeddings = embedder.embed_documents([c.text for c in chunks])
    store.delete_cryptid(ref.name)
    store.add_chunks(
        cryptid_name=ref.name,
        category=ref.category,
        source=source,
        chunk_texts=[c.text for c in chunks],
        chunk_sections=[c.section for c in chunks],
        chunk_indices=[c.chunk_index for c in chunks],
        embeddings=embeddings,
    )
    store.add_article(
        cryptid_name=ref.name,
        category=ref.category,
        source=source,
        full_text=fetched.full_text,
        aliases=fetched.aliases,
        content_hash=fetched.content_hash,
    )


def _print_bucket(label: str, names: list[str]) -> None:
    print(f"{label}: {len(names)}")
    for name in names:
        print(f"  {name}")


def run(store: Store | None = None, embedder: VoyageEmbedder | None = None) -> None:
    store = store or Store()
    embedder = embedder or VoyageEmbedder()

    print("Fetching taxonomy...")
    taxonomy = fetch_taxonomy()
    taxonomy_by_name = {ref.name: ref for ref in taxonomy}
    taxonomy_names = set(taxonomy_by_name)

    stored_hashes = store.get_stored_hashes()
    stored_names = set(stored_hashes)

    added_names = sorted(taxonomy_names - stored_names)
    removed_names = sorted(stored_names - taxonomy_names)
    candidate_names = sorted(taxonomy_names & stored_names)

    fetched_by_name: dict[str, _Fetched] = {}
    changed_names: list[str] = []
    unchanged_names: list[str] = []

    for name in added_names + candidate_names:
        fetched = _fetch(taxonomy_by_name[name])
        if fetched is None:
            continue
        if name in stored_hashes and fetched.content_hash == stored_hashes[name]:
            unchanged_names.append(name)
        else:
            fetched_by_name[name] = fetched
            if name in stored_hashes:
                changed_names.append(name)
    added_names = [name for name in added_names if name in fetched_by_name]

    print("\n--- Dry run summary ---")
    _print_bucket("Added", added_names)
    _print_bucket("Changed", changed_names)
    _print_bucket("Removed", removed_names)
    _print_bucket("Unchanged", unchanged_names)

    if not added_names and not changed_names and not removed_names:
        print("\nNothing to do.")
        return

    answer = input("\nProceed? [y/N] ").strip().lower()
    if answer != "y":
        print("Aborted.")
        return

    for name in added_names + changed_names:
        _insert(store, embedder, fetched_by_name[name])
    for name in removed_names:
        store.delete_cryptid(name)

    print(f"Done. {len(added_names)} added, {len(changed_names)} changed, {len(removed_names)} removed.")


def main() -> None:
    try:
        run()
    except EmbeddingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
