"""Embedding model wrapper — always runs on CPU.

GPU memory is reserved for LLM generation. The embedding model is small
(~80 MB) and runs fast enough on CPU for single-query RAG retrieval.
"""
from __future__ import annotations

import torch
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """Wraps SentenceTransformer with CPU-only enforcement and batch encoding."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str | None = None):
        self.model_name = model_name
        # Always use CPU — GPU is reserved for LLM generation
        self.device = "cpu"
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            print(f"Loading embedding model '{self.model_name}' on CPU...")
            self._model = SentenceTransformer(self.model_name, device="cpu")
            print("Embedding model loaded on CPU.")
        return self._model

    def encode(self, texts: list[str], batch_size: int = 256, show_progress_bar: bool = False):
        return self.model.encode(
            texts,
            batch_size=batch_size,
            device="cpu",
            show_progress_bar=show_progress_bar,
            convert_to_numpy=True,
        )
