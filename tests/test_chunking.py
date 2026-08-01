from sitt_rag.chunking import chunk_article, count_tokens
from sitt_rag.wikipedia import Article, Section


def make_paragraph(word: str, n_tokens: int) -> str:
    # cl100k_base tokenizes simple repeated words at ~1 token each.
    return " ".join([word] * n_tokens)


def test_small_section_stays_as_one_chunk():
    article = Article(
        title="Test Cryptid",
        sections=[Section(title="Lead", paragraphs=["A short paragraph.", "Another short one."])],
    )
    chunks = chunk_article(article, budget=500, overlap_paragraphs=1)
    assert len(chunks) == 1
    assert chunks[0].section == "Lead"
    assert chunks[0].chunk_index == 0
    assert "A short paragraph." in chunks[0].text
    assert "Another short one." in chunks[0].text


def test_oversized_section_splits_with_overlap():
    paragraphs = [make_paragraph(f"p{i}word", 300) for i in range(4)]
    article = Article(title="Test Cryptid", sections=[Section(title="Body", paragraphs=paragraphs)])

    chunks = chunk_article(article, budget=500, overlap_paragraphs=1)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.section == "Body"
    # consecutive chunk_index values, starting at 0
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    # the last paragraph of one part reappears as the first paragraph of the next (1-paragraph overlap)
    first_part_paragraphs = chunks[0].text.split("\n\n")
    second_part_paragraphs = chunks[1].text.split("\n\n")
    assert first_part_paragraphs[-1] == second_part_paragraphs[0]


def test_chunk_index_is_global_across_sections():
    article = Article(
        title="Test Cryptid",
        sections=[
            Section(title="Lead", paragraphs=["Lead paragraph."]),
            Section(title="History", paragraphs=["History paragraph."]),
        ],
    )
    chunks = chunk_article(article, budget=500, overlap_paragraphs=1)
    assert [c.chunk_index for c in chunks] == [0, 1]
    assert [c.section for c in chunks] == ["Lead", "History"]


def test_count_tokens_nonzero_for_text():
    assert count_tokens("The bunyip is a creature from Aboriginal mythology.") > 0
    assert count_tokens("") == 0
