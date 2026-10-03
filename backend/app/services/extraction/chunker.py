"""
Document chunking with preserved character offsets for exact evidence citation.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    start_offset: int
    end_offset: int
    chunk_index: int


def split_into_chunks(text: str, max_chars: int = 1500, overlap: int = 200) -> list[Chunk]:
    """Split text into overlapping chunks preserving character offsets."""
    chunks: list[Chunk] = []
    start = 0
    total_len = len(text)

    if not text:
        return []

    while start < total_len:
        end = min(start + max_chars, total_len)
        if end < total_len:
            # Prefer paragraph boundary
            nl = text.rfind("\n", start, end)
            if nl > start + (max_chars // 2):
                end = nl + 1

        chunk_text = text[start:end]
        chunks.append(
            Chunk(
                text=chunk_text,
                start_offset=start,
                end_offset=end,
                chunk_index=len(chunks),
            )
        )

        if end >= total_len:
            break
        start = end - overlap
        if start <= 0 or start >= end:
            start = end

    return chunks
