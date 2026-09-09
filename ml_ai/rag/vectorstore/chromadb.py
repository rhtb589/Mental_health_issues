"""ChromaDB vector store wrapper."""
from __future__ import annotations

import chromadb


class ChromaVectorStore:
    """Manages ChromaDB collection for document embeddings."""

    def __init__(self, persist_dir: str, collection_name: str = "mental_health_docs", distance: str = "cosine"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.distance = distance
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.PersistentClient(path=self.persist_dir)
        return self._client

    @property
    def collection(self) -> chromadb.Collection:
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": self.distance},
            )
        return self._collection

    def reset(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = None

    def upsert(self, ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]) -> None:
        self.collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def query(self, query_embeddings: list[list[float]], n_results: int = 5, include: list[str] | None = None) -> dict:
        include = include or ["documents", "metadatas", "distances"]
        return self.collection.query(query_embeddings=query_embeddings, n_results=n_results, include=include)

    def count(self) -> int:
        return self.collection.count()
