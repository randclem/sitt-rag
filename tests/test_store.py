from sitt_rag.store import CryptidSummary, Source, Store


def test_add_chunks_and_search_roundtrip(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()

    source = Source(title="Bunyip", url="https://en.wikipedia.org/wiki/Bunyip", license="CC BY-SA 4.0")

    store.add_chunks(
        cryptid_name="Bunyip",
        category="Aquatic or semi-aquatic",
        source=source,
        chunk_texts=["The bunyip lurks in swamps.", "It is part of Aboriginal mythology."],
        chunk_sections=["Lead", "Lead"],
        chunk_indices=[0, 1],
        embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
    )
    store.add_article(
        cryptid_name="Bunyip",
        category="Aquatic or semi-aquatic",
        source=source,
        full_text="## Lead\n\nThe bunyip lurks in swamps.",
        aliases=["Bunyips", "Bunjip"],
    )

    results = store.search(query_embedding=[1.0, 0.0, 0.0], top_k=5)

    assert len(results) == 2
    assert results[0].cryptid_name == "Bunyip"
    assert results[0].text == "The bunyip lurks in swamps."
    assert results[0].source.title == "Bunyip"
    # the closer embedding should rank first
    assert results[0].score > results[1].score


def test_add_article_with_no_aliases(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="Anguila peluda", url="https://en.wikipedia.org/wiki/Anguila_peluda", license="CC BY-SA 4.0")

    store.add_article(
        cryptid_name="Anguila peluda",
        category="Aquatic or semi-aquatic",
        source=source,
        full_text="## Lead\n\nSome text.",
        aliases=[],
    )

    assert store.articles.count() == 1


def test_get_article_resolves_by_canonical_name_case_insensitively(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="Jersey Devil", url="https://en.wikipedia.org/wiki/Jersey_Devil", license="CC BY-SA 4.0")
    store.add_article(
        cryptid_name="Jersey Devil",
        category="North America",
        source=source,
        full_text="## Lead\n\nThe Jersey Devil is a legendary creature.",
        aliases=["Leeds Devil"],
    )

    exact = store.get_article("Jersey Devil")
    lowercased = store.get_article("jersey devil")

    assert exact is not None
    assert exact.name == "Jersey Devil"
    assert exact.text == "## Lead\n\nThe Jersey Devil is a legendary creature."
    assert exact.source.title == "Jersey Devil"
    assert lowercased is not None
    assert lowercased.name == "Jersey Devil"


def test_get_article_resolves_by_alias(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="Jersey Devil", url="https://en.wikipedia.org/wiki/Jersey_Devil", license="CC BY-SA 4.0")
    store.add_article(
        cryptid_name="Jersey Devil",
        category="North America",
        source=source,
        full_text="## Lead\n\nThe Jersey Devil is a legendary creature.",
        aliases=["Leeds Devil"],
    )

    result = store.get_article("leeds devil")

    assert result is not None
    assert result.name == "Jersey Devil"


def test_get_article_returns_none_when_not_found(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="Jersey Devil", url="https://en.wikipedia.org/wiki/Jersey_Devil", license="CC BY-SA 4.0")
    store.add_article(
        cryptid_name="Jersey Devil",
        category="North America",
        source=source,
        full_text="## Lead\n\nThe Jersey Devil is a legendary creature.",
        aliases=["Leeds Devil"],
    )

    assert store.get_article("Mothman") is None


def test_list_categories_returns_sorted_unique_categories(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="X", url="https://example.com", license="CC BY-SA 4.0")
    store.add_article(cryptid_name="Bunyip", category="Australia", source=source, full_text="t", aliases=[])
    store.add_article(cryptid_name="Jersey Devil", category="North America", source=source, full_text="t", aliases=[])
    store.add_article(cryptid_name="Yowie", category="Australia", source=source, full_text="t", aliases=[])

    assert store.list_categories() == ["Australia", "North America"]


def test_list_cryptids_returns_all_entries_sorted_by_name(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="X", url="https://example.com", license="CC BY-SA 4.0")
    store.add_article(cryptid_name="Yowie", category="Australia", source=source, full_text="t", aliases=[])
    store.add_article(cryptid_name="Bunyip", category="Australia", source=source, full_text="t", aliases=[])

    entries = store.list_cryptids()

    assert entries == [
        CryptidSummary(name="Bunyip", category="Australia"),
        CryptidSummary(name="Yowie", category="Australia"),
    ]


def test_list_cryptids_filters_by_category_case_insensitively(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="X", url="https://example.com", license="CC BY-SA 4.0")
    store.add_article(cryptid_name="Bunyip", category="Australia", source=source, full_text="t", aliases=[])
    store.add_article(cryptid_name="Jersey Devil", category="North America", source=source, full_text="t", aliases=[])

    entries = store.list_cryptids(category="australia")

    assert entries == [CryptidSummary(name="Bunyip", category="Australia")]


def test_list_cryptids_returns_none_for_unknown_category(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="X", url="https://example.com", license="CC BY-SA 4.0")
    store.add_article(cryptid_name="Bunyip", category="Australia", source=source, full_text="t", aliases=[])

    assert store.list_cryptids(category="not a real category") is None


def test_list_cryptids_treats_blank_category_as_no_filter(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="X", url="https://example.com", license="CC BY-SA 4.0")
    store.add_article(cryptid_name="Bunyip", category="Australia", source=source, full_text="t", aliases=[])

    assert store.list_cryptids(category="  ") == [CryptidSummary(name="Bunyip", category="Australia")]


def test_add_article_stores_content_hash_and_get_stored_hashes_returns_it(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="Bunyip", url="https://en.wikipedia.org/wiki/Bunyip", license="CC BY-SA 4.0")

    store.add_article(
        cryptid_name="Bunyip", category="Australia", source=source, full_text="t", aliases=[], content_hash="abc123"
    )

    assert store.get_stored_hashes() == {"Bunyip": "abc123"}


def test_get_stored_hashes_returns_empty_dict_when_no_articles(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()

    assert store.get_stored_hashes() == {}


def test_delete_cryptid_removes_chunks_and_article(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="Bunyip", url="https://en.wikipedia.org/wiki/Bunyip", license="CC BY-SA 4.0")
    store.add_chunks(
        cryptid_name="Bunyip",
        category="Australia",
        source=source,
        chunk_texts=["text"],
        chunk_sections=["Lead"],
        chunk_indices=[0],
        embeddings=[[1.0, 0.0]],
    )
    store.add_article(
        cryptid_name="Bunyip", category="Australia", source=source, full_text="t", aliases=[], content_hash="abc123"
    )
    store.add_chunks(
        cryptid_name="Yowie",
        category="Australia",
        source=source,
        chunk_texts=["other text"],
        chunk_sections=["Lead"],
        chunk_indices=[0],
        embeddings=[[0.0, 1.0]],
    )
    store.add_article(
        cryptid_name="Yowie", category="Australia", source=source, full_text="t2", aliases=[], content_hash="def456"
    )

    store.delete_cryptid("Bunyip")

    assert store.get_stored_hashes() == {"Yowie": "def456"}
    remaining_chunks = store.chunks.get(include=["metadatas"])
    assert [m["cryptid_name"] for m in remaining_chunks["metadatas"]] == ["Yowie"]


def test_delete_cryptid_is_a_noop_when_not_present(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()

    store.delete_cryptid("Nonexistent")  # should not raise

    assert store.get_stored_hashes() == {}


def test_reset_clears_previous_data(tmp_path):
    store = Store(data_dir=tmp_path)
    store.reset()
    source = Source(title="X", url="https://example.com", license="CC BY-SA 4.0")
    store.add_chunks(
        cryptid_name="X",
        category="Terrestrial",
        source=source,
        chunk_texts=["text"],
        chunk_sections=["Lead"],
        chunk_indices=[0],
        embeddings=[[1.0, 0.0]],
    )

    store.reset()

    assert store.chunks.count() == 0
