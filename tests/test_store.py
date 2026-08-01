from sitt_rag.store import Source, Store


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
