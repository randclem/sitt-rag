"""Section-based chunking: merge consecutive paragraphs up to a token budget,
splitting oversized sections at paragraph boundaries with a paragraph of overlap.
"""

from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from sitt_rag.config import CHUNK_OVERLAP_PARAGRAPHS, CHUNK_TOKEN_BUDGET
from sitt_rag.wikipedia import Article

_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


@dataclass
class Chunk:
    text: str
    section: str
    chunk_index: int


def _split_section(paragraphs: list[str], budget: int, overlap_paragraphs: int) -> list[list[str]]:
    """Greedily group paragraphs up to `budget` tokens, carrying the last
    `overlap_paragraphs` paragraphs of a part forward into the next one.
    """
    parts: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0

    for paragraph in paragraphs:
        paragraph_tokens = count_tokens(paragraph)
        if current and current_tokens + paragraph_tokens > budget:
            parts.append(current)
            current = current[-overlap_paragraphs:] if overlap_paragraphs else []
            current_tokens = sum(count_tokens(p) for p in current)
        current.append(paragraph)
        current_tokens += paragraph_tokens

    if current:
        parts.append(current)
    return parts


def chunk_article(
    article: Article,
    budget: int = CHUNK_TOKEN_BUDGET,
    overlap_paragraphs: int = CHUNK_OVERLAP_PARAGRAPHS,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_index = 0
    for section in article.sections:
        for part in _split_section(section.paragraphs, budget, overlap_paragraphs):
            chunks.append(
                Chunk(text="\n\n".join(part), section=section.title, chunk_index=chunk_index)
            )
            chunk_index += 1
    return chunks
