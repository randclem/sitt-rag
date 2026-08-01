from sitt_rag import server
from sitt_rag.store import SearchResult, Source


class FakeEmbedder:
    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


class FakeStore:
    def search(self, query_embedding, top_k):
        assert top_k <= server.MAX_TOP_K
        return [
            SearchResult(
                text="The bunyip lurks in swamps.",
                cryptid_name="Bunyip",
                score=0.9,
                source=Source(title="Bunyip", url="https://en.wikipedia.org/wiki/Bunyip", license="CC BY-SA 4.0"),
            )
        ]


def test_search_cryptid_lore_returns_ranked_results(monkeypatch):
    monkeypatch.setattr(server, "_get_embedder", lambda: FakeEmbedder())
    monkeypatch.setattr(server, "_get_store", lambda: FakeStore())

    results = server.search_cryptid_lore("sasquatch sightings", top_k=5)

    assert isinstance(results, list)
    assert results[0]["cryptid_name"] == "Bunyip"
    assert results[0]["source"]["license"] == "CC BY-SA 4.0"


def test_search_cryptid_lore_clamps_top_k(monkeypatch):
    monkeypatch.setattr(server, "_get_embedder", lambda: FakeEmbedder())
    monkeypatch.setattr(server, "_get_store", lambda: FakeStore())

    server.search_cryptid_lore("query", top_k=999)  # FakeStore asserts the clamp


def test_search_cryptid_lore_rejects_empty_query():
    result = server.search_cryptid_lore("   ", top_k=5)
    assert result["error"]["code"] == "invalid_argument"


def test_search_cryptid_lore_returns_error_envelope_when_embedding_fails(monkeypatch):
    class FailingEmbedder:
        def embed_query(self, text):
            raise RuntimeError("network down")

    monkeypatch.setattr(server, "_get_embedder", lambda: FailingEmbedder())

    result = server.search_cryptid_lore("query", top_k=5)

    assert result["error"]["code"] == "embedding_failed"
