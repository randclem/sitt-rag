"""ChromaDB storage layer: two collections, `chunks` (embedded, searched) and
`articles` (unembedded, full text), backed by a local persistent client.
"""

from __future__ import annotations

from dataclasses import dataclass

import chromadb

from sitt_rag.config import DATA_DIR

CHUNKS_COLLECTION = "chunks"
ARTICLES_COLLECTION = "articles"


@dataclass
class Source:
    title: str
    url: str
    license: str


@dataclass
class SearchResult:
    text: str
    cryptid_name: str
    score: float
    source: Source


@dataclass
class ArticleResult:
    name: str
    text: str
    source: Source


@dataclass
class CryptidSummary:
    name: str
    category: str


class Store:
    def __init__(self, data_dir=DATA_DIR):
        data_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(data_dir))

    def reset(self) -> None:
        """Drop and recreate both collections — used for the full-rebuild ingest."""
        for name in (CHUNKS_COLLECTION, ARTICLES_COLLECTION):
            try:
                self._client.delete_collection(name)
            except Exception:
                pass
        self.chunks
        self.articles

    @property
    def chunks(self):
        return self._client.get_or_create_collection(
            CHUNKS_COLLECTION, embedding_function=None, metadata={"hnsw:space": "cosine"}
        )

    @property
    def articles(self):
        return self._client.get_or_create_collection(ARTICLES_COLLECTION, embedding_function=None)

    def add_chunks(
        self,
        cryptid_name: str,
        category: str,
        source: Source,
        chunk_texts: list[str],
        chunk_sections: list[str],
        chunk_indices: list[int],
        embeddings: list[list[float]],
    ) -> None:
        if not chunk_texts:
            return
        ids = [f"{cryptid_name}::{i}" for i in chunk_indices]
        metadatas = [
            {
                "cryptid_name": cryptid_name,
                "category": category,
                "section": section,
                "chunk_index": index,
                "source_title": source.title,
                "source_url": source.url,
                "source_license": source.license,
            }
            for section, index in zip(chunk_sections, chunk_indices)
        ]
        self.chunks.add(ids=ids, embeddings=embeddings, documents=chunk_texts, metadatas=metadatas)

    def add_article(
        self,
        cryptid_name: str,
        category: str,
        source: Source,
        full_text: str,
        aliases: list[str],
    ) -> None:
        metadata = {
            "cryptid_name": cryptid_name,
            "category": category,
            "source_title": source.title,
            "source_url": source.url,
            "source_license": source.license,
        }
        if aliases:
            metadata["aliases"] = aliases
        self.articles.add(ids=[cryptid_name], documents=[full_text], metadatas=[metadata])

    def get_article(self, name: str) -> ArticleResult | None:
        """Resolve `name` case-insensitively against canonical title, then alias."""
        result = self.articles.get(include=["documents", "metadatas"])
        ids = result["ids"]
        documents = result["documents"]
        metadatas = result["metadatas"]
        target = name.strip().lower()

        for cryptid_name, document, metadata in zip(ids, documents, metadatas):
            if cryptid_name.lower() == target:
                return self._to_article_result(cryptid_name, document, metadata)

        for cryptid_name, document, metadata in zip(ids, documents, metadatas):
            aliases = metadata.get("aliases") or []
            if any(alias.lower() == target for alias in aliases):
                return self._to_article_result(cryptid_name, document, metadata)

        return None

    def _to_article_result(self, cryptid_name: str, document: str, metadata: dict) -> ArticleResult:
        return ArticleResult(
            name=cryptid_name,
            text=document,
            source=Source(
                title=metadata["source_title"],
                url=metadata["source_url"],
                license=metadata["source_license"],
            ),
        )

    def _all_cryptid_summaries(self) -> list[CryptidSummary]:
        result = self.articles.get(include=["metadatas"])
        return [
            CryptidSummary(name=cryptid_name, category=metadata["category"])
            for cryptid_name, metadata in zip(result["ids"], result["metadatas"])
        ]

    def list_categories(self) -> list[str]:
        """Return the sorted, deduplicated set of categories present in ingested articles."""
        return sorted({summary.category for summary in self._all_cryptid_summaries()})

    def list_cryptids(self, category: str | None = None) -> list[CryptidSummary] | None:
        """Return every ingested cryptid's {name, category}, sorted by name.

        `category` filters case-insensitively; a blank/omitted category returns the
        full list. An unrecognized category returns `None` (consistent with
        `get_article`'s not-found signal).
        """
        summaries = self._all_cryptid_summaries()
        if category is not None and category.strip():
            target = category.strip().lower()
            summaries = [s for s in summaries if s.category.lower() == target]
            if not summaries:
                return None
        summaries.sort(key=lambda s: s.name)
        return summaries

    def search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]:
        result = self.chunks.query(query_embeddings=[query_embedding], n_results=top_k)
        results: list[SearchResult] = []
        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]
        for _id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            results.append(
                SearchResult(
                    text=document,
                    cryptid_name=metadata["cryptid_name"],
                    score=1.0 - distance,
                    source=Source(
                        title=metadata["source_title"],
                        url=metadata["source_url"],
                        license=metadata["source_license"],
                    ),
                )
            )
        return results
