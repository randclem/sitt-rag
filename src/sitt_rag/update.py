"""Incremental ingest: diff the current "List of cryptids" taxonomy against what's
already stored, fetch only what's added or changed, hard-delete what's gone, and
require a `[y/N]` confirmation before writing anything.

A cryptid whose article can't be fetched or parsed lands in a `failed` bucket
instead of aborting the run: it's excluded from this run's commit, its existing
rows are left in place, and it reappears in the same bucket on the next run.

Usage: python -m sitt_rag.update [--eval]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass

from sitt_rag.chunking import chunk_article
from sitt_rag.config import CC_BY_SA_LICENSE, WIKIPEDIA_ORIGIN
from sitt_rag.embeddings import EmbeddingError, VoyageEmbedder
from sitt_rag.eval import EvalError
from sitt_rag.store import Source, Store
from sitt_rag.wikipedia import Article, CryptidRef, WikipediaError, fetch_article, fetch_redirects, fetch_taxonomy


def article_url(title: str) -> str:
    return f"{WIKIPEDIA_ORIGIN}/wiki/{title.replace(' ', '_')}"


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


@dataclass
class _Failure:
    cryptid_name: str
    url: str
    error: str


def _fetch(ref: CryptidRef) -> _Fetched | _Failure:
    """Fetch and hash one cryptid's article, returning a `_Failure` rather than raising —
    the run continues, leaving any existing stored data for this cryptid untouched."""
    try:
        article = fetch_article(ref.wikipedia_title)
        aliases = fetch_redirects(ref.wikipedia_title)
    except WikipediaError as exc:
        return _Failure(cryptid_name=ref.name, url=article_url(ref.wikipedia_title), error=str(exc))
    text = full_text_for(article)
    return _Fetched(ref=ref, article=article, aliases=aliases, full_text=text, content_hash=content_hash(text))


def _insert(store: Store, embedder: VoyageEmbedder, fetched: _Fetched) -> None:
    ref = fetched.ref
    source = Source(
        title=fetched.article.title,
        url=article_url(fetched.article.title),
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


def _report_failures(failures: list[_Failure]) -> None:
    """Print every fetch failure from this run, with the URL and reason for each."""
    if not failures:
        return
    print(f"\n{len(failures)} cryptid(s) failed to fetch and were left untouched:")
    for failure in failures:
        print(f"  {failure.cryptid_name} ({failure.url}): {failure.error}")


def run(store: Store | None = None, embedder: VoyageEmbedder | None = None) -> bool:
    """Diff, fetch and (on confirmation) commit. Returns False if the user declined."""
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
    failures: list[_Failure] = []

    # Change detection needs the article's full text in hand to hash it, so fetch
    # failures surface here, during the dry run, and are excluded from this run's commit.
    for name in added_names + candidate_names:
        fetched = _fetch(taxonomy_by_name[name])
        if isinstance(fetched, _Failure):
            failures.append(fetched)
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
    _print_bucket("Failed", [failure.cryptid_name for failure in failures])

    if not added_names and not changed_names and not removed_names:
        print("\nNothing to do.")
        _report_failures(failures)
        return True

    answer = input("\nProceed? [y/N] ").strip().lower()
    if answer != "y":
        print("Aborted.")
        _report_failures(failures)
        return False

    for name in added_names + changed_names:
        _insert(store, embedder, fetched_by_name[name])
    for name in removed_names:
        store.delete_cryptid(name)

    print(f"Done. {len(added_names)} added, {len(changed_names)} changed, {len(removed_names)} removed.")
    _report_failures(failures)
    return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m sitt_rag.update",
        description="Diff the cryptid taxonomy against the store and ingest what changed.",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="after updating, score search_cryptid_lore's Recall@5 against the golden query set",
    )
    args = parser.parse_args(argv)

    try:
        committed = run()
        # Declining the [y/N] prompt means "stop" — don't then spend a Voyage
        # query embedding per golden query scoring a store the user left alone.
        if args.eval and committed:
            from sitt_rag.eval import run as run_eval

            print()
            run_eval()
    except (EmbeddingError, WikipediaError, EvalError) as exc:
        # Per-cryptid fetch failures are absorbed into the failed bucket; a
        # WikipediaError reaching here means the taxonomy itself is unreachable,
        # so there's nothing to diff against. An EvalError means --eval couldn't
        # read its golden set — the ingest above still stands.
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
