"""Text chunking for RAG ingestion pipeline."""
from __future__ import annotations

import re


class TextChunker:
    """Sentence-aware text chunker with configurable overlap."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) + 1 > self.chunk_size and current:
                chunks.append(current.strip())
                words = current.split()
                n = self.chunk_overlap // 6
                overlap_text = " ".join(words[-n:]) if len(words) > n else ""
                current = f"{overlap_text} {sentence}".strip() if overlap_text else sentence
            else:
                current = f"{current} {sentence}".strip() if current else sentence

        if current.strip():
            chunks.append(current.strip())

        return chunks if chunks else [text[: self.chunk_size]]
