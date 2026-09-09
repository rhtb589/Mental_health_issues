"""Vector database builder — thin orchestrator.

Uses modular RAG components:
  - ingestion/pdf_loader.py    — PDF text extraction
  - ingestion/chunker.py       — text chunking
  - ingestion/document_cleaner.py — text cleaning
  - ingestion/metadata_extractor.py — metadata helpers
  - embeddings/embedding_model.py — model wrapper
  - vectorstore/chromadb.py    — vector store operations

Usage:
    python -m ml_ai.rag.embeddings.generation
    python -m ml_ai.rag.embeddings.generation --rebuild
    python -m ml_ai.rag.embeddings.generation --query "What are symptoms of depression?"
    python -m ml_ai.rag.embeddings.generation --device cpu
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import pandas as pd
import yaml

from ml_ai.rag.ingestion.document_cleaner import clean_text
from ml_ai.rag.ingestion.chunker import TextChunker
from ml_ai.rag.ingestion.metadata_extractor import build_metadata
from ml_ai.rag.ingestion.pdf_loader import PDFLoader
from ml_ai.rag.embeddings.embedding_model import EmbeddingModel
from ml_ai.rag.vectorstore.chromadb import ChromaVectorStore

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASETS_DIR = PROJECT_ROOT / "datasets"
CONFIG_PATH = Path(__file__).parent / "embedding_config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def build_vectordb(
    rebuild: bool = False,
    query: str | None = None,
    query_limit: int = 5,
    device: str | None = None,
) -> None:
    cfg = load_config()

    # --- Vector store ---
    chroma_dir = str(PROJECT_ROOT / cfg["storage"]["path"])
    store = ChromaVectorStore(
        persist_dir=chroma_dir,
        collection_name=cfg["storage"]["collection"],
        distance=cfg["storage"]["distance"],
    )

    if rebuild:
        store.reset()
        print("Deleted existing collection.")

    # --- Query mode ---
    if query:
        model = EmbeddingModel(model_name=cfg["model"]["name"], device=device)
        emb = model.encode([query], batch_size=cfg["model"]["batch_size"][model.device]).tolist()
        results = store.query(query_embeddings=emb, n_results=query_limit)
        print(f"\nQuery: {query}\nResults ({len(results['ids'][0])}):\n")
        for i, (doc, meta, dist) in enumerate(
            zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
        ):
            print(f"--- Result {i+1} (distance: {dist:.4f}) ---")
            print(f"Source: {meta.get('source', '?')} | Type: {meta.get('doc_type', '?')}")
            print(doc[:300] + ("..." if len(doc) > 300 else ""))
            print()
        return

    # --- Check existing ---
    if store.count() > 0 and not rebuild:
        print(f"Collection has {store.count()} docs. Use --rebuild to recreate, --query to search.")
        return

    # --- Extract & chunk ---
    pdf_loader = PDFLoader()
    chunker = TextChunker(
        chunk_size=cfg["chunking"]["chunk_size"],
        chunk_overlap=cfg["chunking"]["chunk_overlap"],
    )

    all_chunks: list[dict] = []

    for pdf_name in cfg["ingestion"]["pdf_files"]:
        pdf_path = DATASETS_DIR / pdf_name
        if not pdf_path.exists():
            print(f"  Skipping {pdf_name} (not found)")
            continue
        print(f"  Extracting: {pdf_name}")
        for page_data in pdf_loader.load(pdf_path):
            for ci, chunk in enumerate(chunker.chunk(clean_text(page_data["text"]))):
                meta = build_metadata(
                    source=pdf_name,
                    doc_type="pdf",
                    page=page_data["page"],
                    chunk_index=ci,
                )
                all_chunks.append({
                    "id": f"{pdf_name}_p{page_data['page']}_c{ci}",
                    "text": chunk,
                    "metadata": meta,
                })

    csv_path = DATASETS_DIR / cfg["ingestion"]["csv_file"]
    if csv_path.exists():
        print(f"  Extracting: {cfg['ingestion']['csv_file']}")
        df = pd.read_csv(csv_path)
        df = df[df["text"].notna() & (df["text"].str.strip().str.len() >= 10)]
        max_rows = cfg["ingestion"]["max_csv_rows"]
        if len(df) > max_rows:
            n_groups = max(df["status"].nunique(), 1)
            df = df.groupby("status", group_keys=False).apply(
                lambda x: x.sample(n=min(len(x), max_rows // n_groups), random_state=42)
            )
        for idx, row in df.iterrows():
            text = str(row.get("text", "")).strip()
            status = str(row.get("status", "")).strip()
            if not text or text == "nan":
                continue
            if status == "nan":
                status = ""
            text_hash = hashlib.md5(f"{text}_{idx}".encode()).hexdigest()[:12]
            clean = clean_text(f"[{status}] {text}" if status else text)
            meta = build_metadata(
                source=cfg["ingestion"]["csv_file"],
                doc_type="csv",
                row_id=idx,
                status=status,
            )
            all_chunks.append({
                "id": f"csv_{text_hash}",
                "text": clean,
                "metadata": meta,
            })

    print(f"\nTotal chunks to embed: {len(all_chunks)}")

    # --- Encode & store ---
    model = EmbeddingModel(model_name=cfg["model"]["name"], device=device)
    batch_size = cfg["model"]["batch_size"][model.device]
    total_batches = (len(all_chunks) + batch_size - 1) // batch_size

    t0 = time.time()
    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(all_chunks))
        batch = all_chunks[start:end]

        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadatas = [c["metadata"] for c in batch]

        embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False).tolist()
        store.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

        elapsed = time.time() - t0
        rate = end / elapsed if elapsed > 0 else 0
        eta = (len(all_chunks) - end) / rate if rate > 0 else 0
        print(f"  Batch {batch_idx + 1}/{total_batches}  ({end}/{len(all_chunks)} chunks, {rate:.0f} chunks/s, ETA {eta:.0f}s)")

    elapsed = time.time() - t0
    final_count = store.count()
    print(f"\nDone in {elapsed:.1f}s! Vector DB: {chroma_dir}")
    print(f"Collection '{cfg['storage']['collection']}': {final_count} documents")

    # --- Save manifest ---
    manifest = {
        "collection": cfg["storage"]["collection"],
        "embedding_model": cfg["model"]["name"],
        "device": model.device,
        "total_documents": final_count,
        "sources": {},
        "build_time_seconds": round(elapsed, 1),
    }
    for c in all_chunks:
        src = c["metadata"]["source"]
        manifest["sources"][src] = manifest["sources"].get(src, 0) + 1
    with open(DATASETS_DIR / "vectordb_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print("Manifest saved.")


def main():
    parser = argparse.ArgumentParser(description="Build or query the mental health vector database")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild from scratch")
    parser.add_argument("--query", type=str, default=None, help="Search the vector DB")
    parser.add_argument("--query-limit", type=int, default=5, help="Number of results")
    parser.add_argument("--device", type=str, default=None, choices=["cpu", "cuda", "auto"], help="Force device")
    args = parser.parse_args()
    device = args.device if args.device and args.device != "auto" else None
    build_vectordb(rebuild=args.rebuild, query=args.query, query_limit=args.query_limit, device=device)


if __name__ == "__main__":
    main()
