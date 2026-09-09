from __future__ import annotations

from pathlib import Path
import yaml

from ml_ai.rag.embeddings.embedding_model import EmbeddingModel
from ml_ai.rag.vectorstore.chromadb import ChromaVectorStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "ml_ai" / "rag" / "embeddings" / "embedding_config.yaml"

_store = None
_model = None

INSTRUMENT_SOURCE_PRIORITY = {
    "PHQ-9": ["selfhelp.pdf", "mhgap.pdf", "intervention_guide.pdf", "evidence_based_tretment.pdf", "psychology_intervention.pdf"],
    "PHQ-9 (Depression)": ["selfhelp.pdf", "mhgap.pdf", "intervention_guide.pdf", "evidence_based_tretment.pdf", "psychology_intervention.pdf"],
    "GAD-7": ["selfhelp.pdf", "mhgap.pdf", "intervention_guide.pdf", "evidence_based_tretment.pdf", "psychology_intervention.pdf"],
    "GAD-7 (Anxiety)": ["selfhelp.pdf", "mhgap.pdf", "intervention_guide.pdf", "evidence_based_tretment.pdf", "psychology_intervention.pdf"],
    "PHQ-4": ["selfhelp.pdf", "mhgap.pdf", "intervention_guide.pdf", "evidence_based_tretment.pdf"],
    "PHQ-4 (Brief)": ["selfhelp.pdf", "mhgap.pdf", "intervention_guide.pdf", "evidence_based_tretment.pdf"],
    "SAFE-T": ["mhgap.pdf", "intervention_guide.pdf", "evidence_based_tretment.pdf", "selfhelp.pdf"],
    "SAFE-T / C-SSRS (Suicide Risk)": ["mhgap.pdf", "intervention_guide.pdf", "evidence_based_tretment.pdf", "selfhelp.pdf"],
}


def _load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _get_store():
    global _store

    if _store is None:
        cfg = _load_config()
        chroma_dir = str(PROJECT_ROOT / cfg["storage"]["path"])

        _store = ChromaVectorStore(
            persist_dir=chroma_dir,
            collection_name=cfg["storage"]["collection"],
            distance=cfg["storage"]["distance"],
        )

    return _store


def _get_model():
    global _model

    if _model is None:
        cfg = _load_config()
        _model = EmbeddingModel(
            model_name=cfg["model"]["name"],
            device=cfg["model"].get("device", "cpu"),
        )

    return _model


def initialize_retriever():
    """Initialize the embedding model and Chroma store during application startup."""
    model = _get_model()
    store = _get_store()

    # Warm the embedding model so its first real request does not pay
    # model-loading/device-initialization cost.
    model.encode(["MH Care startup warmup"])

    print("Retriever and embedding model loaded.")
    return model, store


def preload():
    """Load the embedding model and ChromaDB store at startup."""
    initialize_retriever()


def retrieve(query: str, n_results: int = 3) -> str:
    model = _get_model()
    store = _get_store()

    emb = model.encode([query]).tolist()
    results = store.query(query_embeddings=emb, n_results=n_results)

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    parts = []
    for doc, meta in zip(docs, metas):
        source = meta.get("source", "unknown")
        parts.append(f"[Source: {source}]\n{doc}")

    return "\n\n".join(parts) if parts else "No relevant knowledge found."


def retrieve_with_context(
    query: str,
    screening_context: str,
    n_results: int = 5,
) -> str:
    model = _get_model()
    store = _get_store()

    augmented_query = f"{query} {screening_context}"
    emb = model.encode([augmented_query]).tolist()

    results = store.query(
        query_embeddings=emb,
        n_results=min(n_results * 3, 30),
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    scored_docs = []

    for doc, meta, dist in zip(docs, metas, distances):
        source = meta.get("source", "unknown")
        scored_docs.append((doc, meta, source, dist))

    scored_docs.sort(key=lambda x: x[3])

    instrument_name = None
    for key in INSTRUMENT_SOURCE_PRIORITY:
        if key.lower() in screening_context.lower():
            instrument_name = key
            break

    priority_sources = INSTRUMENT_SOURCE_PRIORITY.get(instrument_name, [])

    prioritized = []
    other = []

    for doc, meta, source, dist in scored_docs:
        if source in priority_sources:
            prioritized.append((doc, meta, source, dist))
        else:
            other.append((doc, meta, source, dist))

    combined = prioritized + other

    parts = [
        f"[Source: {source}]\n{doc}"
        for doc, meta, source, dist in combined[:n_results]
    ]

    return "\n\n".join(parts) if parts else "No relevant knowledge found."
