"""Metadata helpers for RAG ingestion pipeline."""
from __future__ import annotations


def build_metadata(
    source: str,
    doc_type: str,
    page: int | None = None,
    row_id: int | None = None,
    status: str | None = None,
    chunk_index: int | None = None,
) -> dict:
    meta = {"source": source, "doc_type": doc_type}
    if page is not None:
        meta["page"] = page
    if row_id is not None:
        meta["row_id"] = row_id
    if status is not None:
        meta["status"] = status
    if chunk_index is not None:
        meta["chunk_index"] = chunk_index
    return meta
