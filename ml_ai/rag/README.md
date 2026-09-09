# RAG Embedding Pipeline

Builds a ChromaDB vector database from mental health PDFs and CSV datasets.

## Architecture

```
ml_ai/rag/
├── embeddings/
│   ├── embedding_config.yaml   # All configuration (model, paths, chunking)
│   ├── embedding_model.py      # SentenceTransformer wrapper (GPU/CPU)
│   └── generation.py           # CLI orchestrator — run this file
├── ingestion/
│   ├── pdf_loader.py           # PDF text extraction (pypdf)
│   ├── document_cleaner.py     # Text normalization
│   ├── metadata_extractor.py   # Metadata helpers
│   └── chunker.py              # Sentence-aware text chunking
└── vectorstore/
    └── chromadb.py             # ChromaDB wrapper (upsert, query, reset)
```

## Quick Start

### Build the vector database

```bash
python -m ml_ai.rag.embeddings.generation --rebuild
```

This will:
1. Extract text from 7 PDFs in `datasets/`
2. Extract rows from the CSV in `datasets/research_data/`
3. Clean and chunk all text (500 chars, 80 overlap)
4. Generate embeddings using `all-MiniLM-L6-v2` (auto-detects GPU/CPU)
5. Store everything in `datasets/chroma_db/`
6. Save a manifest to `datasets/vectordb_manifest.json`

### Query the vector database

```bash
# CLI query
python -m ml_ai.rag.embeddings.generation --query "What are symptoms of depression?"

# More results
python -m ml_ai.rag.embeddings.generation --query "self harm prevention" --query-limit 10

# Force CPU
python -m ml_ai.rag.embeddings.generation --query "PTSD symptoms" --device cpu

# Force GPU
python -m ml_ai.rag.embeddings.generation --query "anxiety treatment" --device cuda
```

### Query from Python

```python
from ml_ai.rag.vectorstore.chromadb import ChromaVectorStore
from ml_ai.rag.embedding_model import EmbeddingModel

store = ChromaVectorStore(persist_dir="datasets/chroma_db", collection_name="mental_health_docs")
model = EmbeddingModel(model_name="all-MiniLM-L6-v2")

query = "What are the treatment options for anxiety?"
emb = model.encode([query]).tolist()
results = store.query(query_embeddings=emb, n_results=5)

for i, (doc, meta, dist) in enumerate(zip(results["documents"][0], results["metadatas"][0], results["distances"][0])):
    print(f"[{i+1}] (score: {dist:.4f}) {meta.get('source')}: {doc[:200]}...")
```

## Configuration

Edit `ml_ai/rag/embeddings/embedding_config.yaml`:

```yaml
model:
  name: all-MiniLM-L6-v2
  device: auto        # auto | cpu | cuda
  batch_size:
    cuda: 512
    cpu: 256

chunking:
  chunk_size: 500
  chunk_overlap: 80

storage:
  backend: chroma
  path: datasets/chroma_db
  collection: mental_health_docs
  distance: cosine

ingestion:
  pdf_files:
    - Mental_Health_Disorders_Detailed_Guide.pdf
    - Mental_Health_Disorders_Expanded_Guide.pdf
    - evidence_based_tretment.pdf
    - intervention_guide.pdf
    - mhgap.pdf
    - psychology_intervention.pdf
    - selfhelp.pdf
  csv_file: research_data/mental_health_unbanlanced.csv
  max_csv_rows: 5000
```

## Dependencies

```
sentence-transformers
chromadb
pypdf
pandas
torch
pyyaml
```

## Data Sources

| Source | Type | Description |
|--------|------|-------------|
| `datasets/*.pdf` | PDF | 7 mental health clinical guides |
| `datasets/research_data/*.csv` | CSV | Labeled mental health text data |

## Output

| Path | Description |
|------|-------------|
| `datasets/chroma_db/` | Persistent ChromaDB storage |
| `datasets/vectordb_manifest.json` | Build manifest with source counts |
