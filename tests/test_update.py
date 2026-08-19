from sitt_rag import update
from sitt_rag.store import Source, Store
from sitt_rag.wikipedia import Article, CryptidRef, Section


class FakeEmbedder:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class CountingEmbedder:
    """Like FakeEmbedder, but tracks how many times it was asked to embed —
    used to assert unchanged articles never reach the embedder."""

    def __init__(self) -> None:
        self.calls = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[1.0, 0.0] for _ in texts]


def _bunyip_ref() -> CryptidRef:
    return CryptidRef(name="Bunyip", category="Australia", wikipedia_title="Bunyip")


def _yowie_ref() -> CryptidRef:
    return CryptidRef(name="Yowie", category="Australia", wikipedia_title="Yowie")


def _article(text: str, title: str = "Bunyip") -> Article:
    return Article(title=title, sections=[Section(title="Lead", paragraphs=[text])])


def _seed_bunyip(store: Store, text: str) -> str:
    """Seed the store with a Bunyip article ingested the same way `update.run` would,
    returning the content_hash it was stored under."""
    article = _article(text)
    full_text = update.full_text_for(article)
    content_hash = update.content_hash(full_text)
    source = Source(title="Bunyip", url="https://en.wikipedia.org/wiki/Bunyip", license="CC BY-SA 4.0")
    store.add_chunks(
        cryptid_name="Bunyip",
        category="Australia",
        source=source,
        chunk_texts=[text],
        chunk_sections=["Lead"],
        chunk_indices=[0],
        embeddings=[[1.0, 0.0]],
    )
    store.add_article(
        cryptid_name="Bunyip",
        category="Australia",
        source=source,
        full_text=full_text,
        aliases=[],
        content_hash=content_hash,
    )
    return content_hash


def _wikipedia_fakes(monkeypatch, taxonomy, articles_by_title, redirects_by_title=None):
    redirects_by_title = redirects_by_title or {}
    monkeypatch.setattr(update, "fetch_taxonomy", lambda: taxonomy)
    monkeypatch.setattr(update, "fetch_article", lambda title: articles_by_title[title])
    monkeypatch.setattr(update, "fetch_redirects", lambda title: redirects_by_title.get(title, []))


def test_run_with_no_changes_reports_unchanged_and_makes_no_writes(tmp_path, monkeypatch, capsys):
    store = Store(data_dir=tmp_path)
    store.reset()
    _seed_bunyip(store, "The bunyip lurks in swamps.")

    _wikipedia_fakes(
        monkeypatch,
        taxonomy=[_bunyip_ref()],
        articles_by_title={"Bunyip": _article("The bunyip lurks in swamps.")},
    )
    monkeypatch.setattr("builtins.input", lambda *a: (_ for _ in ()).throw(AssertionError("should not prompt")))

    update.run(store=store, embedder=FakeEmbedder())

    out = capsys.readouterr().out
    assert "Unchanged: 1" in out
    assert "Bunyip" in out  # names are printed per bucket, not just counts
    assert store.chunks.count() == 1
    assert store.articles.count() == 1


def test_run_with_no_changes_does_not_call_embedder(tmp_path, monkeypatch, capsys):
    store = Store(data_dir=tmp_path)
    store.reset()
    _seed_bunyip(store, "The bunyip lurks in swamps.")

    _wikipedia_fakes(
        monkeypatch,
        taxonomy=[_bunyip_ref()],
        articles_by_title={"Bunyip": _article("The bunyip lurks in swamps.")},
    )
    monkeypatch.setattr("builtins.input", lambda *a: (_ for _ in ()).throw(AssertionError("should not prompt")))

    embedder = CountingEmbedder()
    update.run(store=store, embedder=embedder)

    assert embedder.calls == 0


def test_run_detects_changed_article_and_reinserts(tmp_path, monkeypatch, capsys):
    store = Store(data_dir=tmp_path)
    store.reset()
    old_hash = _seed_bunyip(store, "The bunyip lurks in swamps.")

    _wikipedia_fakes(
        monkeypatch,
        taxonomy=[_bunyip_ref()],
        articles_by_title={"Bunyip": _article("The bunyip lurks in billabongs now.")},
    )
    monkeypatch.setattr("builtins.input", lambda *a: "y")

    update.run(store=store, embedder=FakeEmbedder())

    out = capsys.readouterr().out
    assert "Changed: 1" in out
    hashes = store.get_stored_hashes()
    assert hashes["Bunyip"] != old_hash
    chunks = store.chunks.get(include=["documents"])
    assert chunks["documents"] == ["The bunyip lurks in billabongs now."]


def test_run_aborts_without_writes_when_not_confirmed(tmp_path, monkeypatch, capsys):
    store = Store(data_dir=tmp_path)
    store.reset()
    old_hash = _seed_bunyip(store, "The bunyip lurks in swamps.")

    _wikipedia_fakes(
        monkeypatch,
        taxonomy=[_bunyip_ref()],
        articles_by_title={"Bunyip": _article("The bunyip lurks in billabongs now.")},
    )
    monkeypatch.setattr("builtins.input", lambda *a: "n")

    update.run(store=store, embedder=FakeEmbedder())

    out = capsys.readouterr().out
    assert "Aborted" in out
    assert store.get_stored_hashes()["Bunyip"] == old_hash


def test_run_ingests_new_cryptid_via_fresh_insert_path(tmp_path, monkeypatch, capsys):
    store = Store(data_dir=tmp_path)
    store.reset()

    _wikipedia_fakes(
        monkeypatch,
        taxonomy=[_bunyip_ref()],
        articles_by_title={"Bunyip": _article("The bunyip lurks in swamps.")},
        redirects_by_title={"Bunyip": ["Bunyips"]},
    )
    monkeypatch.setattr("builtins.input", lambda *a: "y")

    update.run(store=store, embedder=FakeEmbedder())

    out = capsys.readouterr().out
    assert "Added: 1" in out
    assert store.articles.count() == 1
    assert store.get_stored_hashes()["Bunyip"]


def test_run_hard_deletes_cryptid_removed_from_taxonomy(tmp_path, monkeypatch, capsys):
    store = Store(data_dir=tmp_path)
    store.reset()
    _seed_bunyip(store, "The bunyip lurks in swamps.")

    _wikipedia_fakes(monkeypatch, taxonomy=[], articles_by_title={})
    monkeypatch.setattr("builtins.input", lambda *a: "y")

    update.run(store=store, embedder=FakeEmbedder())

    out = capsys.readouterr().out
    assert "Removed: 1" in out
    assert store.chunks.count() == 0
    assert store.articles.count() == 0


def test_run_handles_added_changed_removed_and_unchanged_together(tmp_path, monkeypatch, capsys):
    store = Store(data_dir=tmp_path)
    store.reset()
    _seed_bunyip(store, "The bunyip lurks in swamps.")
    source = Source(title="Yowie", url="https://en.wikipedia.org/wiki/Yowie", license="CC BY-SA 4.0")
    store.add_chunks(
        cryptid_name="Mothman",
        category="North America",
        source=source,
        chunk_texts=["Mothman text."],
        chunk_sections=["Lead"],
        chunk_indices=[0],
        embeddings=[[1.0, 0.0]],
    )
    store.add_article(
        cryptid_name="Mothman",
        category="North America",
        source=source,
        full_text="## Lead\n\nMothman text.",
        aliases=[],
        content_hash="stale-hash-for-mothman",
    )

    _wikipedia_fakes(
        monkeypatch,
        taxonomy=[_bunyip_ref(), _yowie_ref()],
        articles_by_title={
            "Bunyip": _article("The bunyip lurks in swamps."),  # unchanged
            "Yowie": _article("The yowie roams the outback."),  # added
        },
    )
    monkeypatch.setattr("builtins.input", lambda *a: "y")

    update.run(store=store, embedder=FakeEmbedder())

    out = capsys.readouterr().out
    assert "Added: 1" in out
    assert "Changed: 0" in out
    assert "Removed: 1" in out
    assert "Unchanged: 1" in out

    names = set(store.get_stored_hashes())
    assert names == {"Bunyip", "Yowie"}


def test_run_skips_candidate_fetch_failures_without_aborting(tmp_path, monkeypatch, capsys):
    store = Store(data_dir=tmp_path)
    store.reset()
    old_hash = _seed_bunyip(store, "The bunyip lurks in swamps.")

    def failing_fetch(title):
        raise update.WikipediaError("boom")

    monkeypatch.setattr(update, "fetch_taxonomy", lambda: [_bunyip_ref()])
    monkeypatch.setattr(update, "fetch_article", failing_fetch)
    monkeypatch.setattr(update, "fetch_redirects", lambda title: [])
    monkeypatch.setattr("builtins.input", lambda *a: (_ for _ in ()).throw(AssertionError("should not prompt")))

    update.run(store=store, embedder=FakeEmbedder())

    # last-known-good data untouched
    assert store.get_stored_hashes()["Bunyip"] == old_hash


def test_run_reports_failed_bucket_and_leaves_existing_rows_intact(tmp_path, monkeypatch, capsys):
    store = Store(data_dir=tmp_path)
    store.reset()
    old_hash = _seed_bunyip(store, "The bunyip lurks in swamps.")

    def failing_fetch(title):
        raise update.WikipediaError("404 Not Found")

    monkeypatch.setattr(update, "fetch_taxonomy", lambda: [_bunyip_ref()])
    monkeypatch.setattr(update, "fetch_article", failing_fetch)
    monkeypatch.setattr(update, "fetch_redirects", lambda title: [])
    monkeypatch.setattr("builtins.input", lambda *a: (_ for _ in ()).throw(AssertionError("should not prompt")))

    update.run(store=store, embedder=FakeEmbedder())

    out = capsys.readouterr().out
    assert "Failed: 1" in out
    assert "https://en.wikipedia.org/wiki/Bunyip" in out
    assert "404 Not Found" in out

    # a failed refetch must not delete the cryptid's last-known-good rows
    assert store.get_stored_hashes()["Bunyip"] == old_hash
    assert store.chunks.count() == 1
    assert store.articles.count() == 1


def test_run_continues_past_a_failure_and_ingests_the_rest(tmp_path, monkeypatch, capsys):
    store = Store(data_dir=tmp_path)
    store.reset()

    articles_by_title = {"Yowie": _article("The yowie roams the outback.", title="Yowie")}

    def sometimes_failing_fetch(title):
        if title not in articles_by_title:
            raise update.WikipediaError("connection failed after 3 retries")
        return articles_by_title[title]

    monkeypatch.setattr(update, "fetch_taxonomy", lambda: [_bunyip_ref(), _yowie_ref()])
    monkeypatch.setattr(update, "fetch_article", sometimes_failing_fetch)
    monkeypatch.setattr(update, "fetch_redirects", lambda title: [])
    monkeypatch.setattr("builtins.input", lambda *a: "y")

    update.run(store=store, embedder=FakeEmbedder())

    out = capsys.readouterr().out
    assert "Added: 1" in out
    assert "Failed: 1" in out
    assert set(store.get_stored_hashes()) == {"Yowie"}

    # the surviving cryptid is attributed to its own article, not the failed one's
    stored = store.articles.get(ids=["Yowie"], include=["metadatas"])
    assert stored["metadatas"][0]["source_url"] == "https://en.wikipedia.org/wiki/Yowie"
