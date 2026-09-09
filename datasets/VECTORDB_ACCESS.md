# Vector Database Access Guide

This guide explains how to query the ChromaDB vector database built from all datasets in the `datasets/` folder.

The embedding generation code lives at `ml_ai/rag/embeddings/generation.py`.

---

## Quick Start

```python
import chromadb
from sentence_transformers import SentenceTransformer

# 1. Connect to the vector DB
client = chromadb.PersistentClient(path="datasets/chroma_db")
collection = client.get_collection("mental_health_docs")

# 2. Load the same embedding model used during build
model = SentenceTransformer("all-MiniLM-L6-v2")

# 3. Query
query = "What are symptoms of depression?"
embedding = model.encode([query]).tolist()
results = collection.query(query_embeddings=embedding, n_results=5)

# 4. Read results
for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
    print(f"[{meta['source']}] (score: {1-dist:.4f})")
    print(doc[:200])
    print()
```

---

## Querying by Specific Source File

Each document in the vector DB has a `source` metadata field. Filter by source to search only within a specific file.

### PDF Sources

```python
# Search only in Mental_Health_Disorders_Detailed_Guide.pdf
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={"source": "Mental_Health_Disorders_Detailed_Guide.pdf"}
)

# Search only in mhgap.pdf
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={"source": "mhgap.pdf"}
)

# Search only in intervention_guide.pdf
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={"source": "intervention_guide.pdf"}
)

# Search only in evidence_based_tretment.pdf
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={"source": "evidence_based_tretment.pdf"}
)

# Search only in psychology_intervention.pdf
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={"source": "psychology_intervention.pdf"}
)

# Search only in selfhelp.pdf
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={"source": "selfhelp.pdf"}
)

# Search only in Mental_Health_Disorders_Expanded_Guide.pdf
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={"source": "Mental_Health_Disorders_Expanded_Guide.pdf"}
)
```

### CSV Source (with status filter)

```python
# Search all CSV entries
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={"doc_type": "csv"}
)

# Search only Anxiety entries from CSV
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={
        "$and": [
            {"doc_type": "csv"},
            {"status": "Anxiety"}
        ]
    }
)

# Search only Depression entries from CSV
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={
        "$and": [
            {"doc_type": "csv"},
            {"status": "Depression"}
        ]
    }
)

# Search only Suicidal entries from CSV
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={
        "$and": [
            {"doc_type": "csv"},
            {"status": "Suicidal"}
        ]
    }
)

# Available CSV status values: Anxiety, Depression, Suicidal, Normal, Stress
```

### PDF Page-Specific Search

```python
# Get all chunks from a specific page of a PDF
results = collection.get(
    where={
        "$and": [
            {"source": "mhgap.pdf"},
            {"page": 42}
        ]
    },
    include=["documents", "metadatas"]
)
```

---

## Combining Filters

```python
# Search PDFs only (exclude CSV)
results = collection.query(
    query_embeddings=embedding,
    n_results=10,
    where={"doc_type": "pdf"}
)

# Search specific PDF + page range
results = collection.query(
    query_embeddings=embedding,
    n_results=5,
    where={
        "$and": [
            {"source": "intervention_guide.pdf"},
            {"page": {"$gte": 10}},
            {"page": {"$lte": 50}}
        ]
    }
)
```

---

## Getting Collection Stats

```python
# Total document count
print(f"Total documents: {collection.count()}")

# Get all unique sources
all_docs = collection.get(include=["metadatas"])
sources = set(m["source"] for m in all_docs["metadatas"])
for src in sorted(sources):
    count = sum(1 for m in all_docs["metadatas"] if m["source"] == src)
    print(f"  {src}: {count} chunks")
```

---

## CLI Usage

```bash
# Rebuild the entire vector DB
python -m ml_ai.rag.embeddings.generation --rebuild

# Query from command line
python -m ml_ai.rag.embeddings.generation --query "anxiety treatment options"

# Query with more results
python -m ml_ai.rag.embeddings.generation --query "self harm prevention" --query-limit 10

# Force GPU
python -m ml_ai.rag.embeddings.generation --query "PTSD symptoms" --device cuda

# Force CPU
python -m ml_ai.rag.embeddings.generation --query "medication for depression" --device cpu
```

---

## Available Source Files

| Source | Chunks | Description |
|--------|--------|-------------|
| `Mental_Health_Disorders_Detailed_Guide.pdf` | 61 | Detailed guide on mental health disorders |
| `Mental_Health_Disorders_Expanded_Guide.pdf` | 69 | Expanded mental health disorders guide |
| `evidence_based_tretment.pdf` | 1,505 | Evidence-based treatment protocols |
| `intervention_guide.pdf` | 874 | Clinical intervention guidelines |
| `mhgap.pdf` | 1,505 | WHO Mental Health Gap Action Programme |
| `psychology_intervention.pdf` | 599 | Psychology intervention methods |
| `selfhelp.pdf` | 869 | Self-help resources |
| `research_data/mental_health_unbanlanced.csv` | 5,000 | User-posted mental health text (Anxiety/Depression/Suicidal/Stress/Normal) |

---

## Example: RAG Integration

```python
def rag_query(question: str, top_k: int = 3) -> str:
    """Retrieve relevant context and return it for an LLM."""
    client = chromadb.PersistentClient(path="datasets/chroma_db")
    collection = client.get_collection("mental_health_docs")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    embedding = model.encode([question]).tolist()
    results = collection.query(
        query_embeddings=embedding,
        n_results=top_k,
        include=["documents", "metadatas"]
    )

    context_parts = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        context_parts.append(f"[Source: {meta['source']}]\n{doc}")

    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: {question}
Answer:"""
    return prompt
```

---

## Sample Search Results

Below are real query results from the vector database, showing what each search returns.

### Query: "symptoms of depression"

| # | Source | Relevance | Content |
|---|--------|-----------|---------|
| 1 | `intervention_guide.pdf` | 69.97% | People with depression experience a range of symptoms including persistent depressed mood or loss of interest and pleasure for at least 2 weeks. People with depression as described in this module have considerable difficulty with daily functioning in personal, family, social, educational, occupational or other areas. Many people with depression also suffer from anxiety symptoms and medically unexplained somatic symptoms. |
| 2 | `Mental_Health_Disorders_Expanded_Guide.pdf` | 68.29% | Depression is a mood disorder characterized by persistent depressed mood and/or loss of interest or pleasure, accompanied by cognitive, physical and behavioral symptoms. It can affect sleep, appetite, energy, concentration, self-worth and functioning. Depression is not simply being sad. It can arise from interacting biological, psychological and social factors. |
| 3 | `Mental_Health_Disorders_Detailed_Guide.pdf` | 67.19% | Depression is more than ordinary sadness. Major depressive episodes involve a persistent depressed mood and/or loss of interest or pleasure together with other symptoms that affect functioning. |

### Query: "anxiety treatment options"

| # | Source | Relevance | Content |
|---|--------|-----------|---------|
| 1 | `Mental_Health_Disorders_Detailed_Guide.pdf` | 75.28% | Evidence-based treatment: Cognitive behavioral therapy and related evidence-based psychotherapies; Exposure-based treatment for phobias, panic and some anxiety presentations; Medication may include certain antidepressants or other clinician-selected options; Relaxation, exercise, sleep and reducing factors that aggravate anxiety can support treatment. |
| 2 | `research_data/mental_health_unbanlanced.csv` | 74.21% | Starting my journey with clinical anxiety disorder, any tips? So yeah, I've finally been diagnosed with anxiety as an actual disorder (generalized anxiety disorder), after many years of thinking it was temporary. I don't feel bad at all, I feel good to finally have my issue recognized on a medical level so I can receive the adequate treatment. |
| 3 | `Mental_Health_Disorders_Detailed_Guide.pdf` | 74.10% | Many anxiety disorders respond well to treatment. Avoidance can maintain anxiety, so carefully planned therapeutic exposure can be an important part of recovery. |

### Query: "suicide prevention interventions"

| # | Source | Relevance | Content |
|---|--------|-----------|---------|
| 1 | `evidence_based_tretment.pdf` | 74.53% | Stallman HM, Allen A. Acute suicide prevention: a systematic review of the evidence and implications for clinical practice. J Affect Disord Rep. 2021;5:100148. |
| 2 | `mhgap.pdf` | 74.53% | Safety planning-type interventions for suicide prevention: meta-analysis. Br J Psychiatry. 2021;219(2):419-26. |
| 3 | `evidence_based_tretment.pdf` | 73.35% | Safety planning-type interventions for suicide prevention: meta-analysis. Br J Psychiatry. 2022;220(4):246. |

### Query: "self help coping strategies"

| # | Source | Relevance | Content |
|---|--------|-----------|---------|
| 1 | `selfhelp.pdf` | 75.41% | Help the person to identify their own coping strategies and support, following the four steps below. When discussing external problems remember to: ask open-ended questions; not rush into providing suggestions too quickly; give the person time to talk and think for themselves. |
| 2 | `selfhelp.pdf` | 74.74% | Psychological self-help interventions. If external problems are preventing someone from progressing with the intervention, you can support their coping strategies by spending a few minutes helping the person to identify their own coping strategies and support. |
| 3 | `selfhelp.pdf` | 74.56% | Psychological self-help interventions: delivering self-help for individuals, featuring Step-by-Step and Doing What Matters in Times of Stress. World Health Organization. |

### Query: "post traumatic stress disorder"

| # | Source | Relevance | Content |
|---|--------|-----------|---------|
| 1 | `intervention_guide.pdf` | 73.48% | After a potentially traumatic event, the person may have PTSD if the symptoms involve considerable difficulty with daily functioning for at least 1 month and include recurring frightening dreams, flashbacks or intrusive memories of the events accompanied by intense fear or horror; deliberate avoidance of reminders of the event; excessive concern and alertness to danger. |
| 2 | `mhgap.pdf` | 72.24% | Post-traumatic stress disorder: the management of PTSD in adults and children in primary and secondary care. Gaskell; 2005. |
| 3 | `evidence_based_tretment.pdf` | 72.24% | Psychological treatment of post-traumatic stress disorder (PTSD). Cochrane Database Syst Rev. 2005;(2):CD003388. |

### Query: "child adolescent mental health"

| # | Source | Relevance | Content |
|---|--------|-----------|---------|
| 1 | `intervention_guide.pdf` | 71.16% | CHILD & ADOLESCENT MENTAL & BEHAVIOURAL DISORDERS. Assess all domains - motor, cognitive, social, communication, and adaptive. |
| 2 | `intervention_guide.pdf` | 70.99% | Emotional disorders are characterized by increased levels of anxiety, depression, fear, and somatic symptoms. Children and adolescents often present with symptoms of more than one condition and sometimes the symptoms overlap. |
| 3 | `psychology_intervention.pdf` | 69.72% | Validation of a brief mental health screening tool for common mental disorders in primary healthcare. |

### Query: "medication for mental illness"

| # | Source | Relevance | Content |
|---|--------|-----------|---------|
| 1 | `psychology_intervention.pdf` | 71.97% | Can be highly effective for many mental health conditions, particularly depression and anxiety. They offer an evidence-based alternative to psychotropic medicines, especially in services that mainly offer medicines to manage mental health conditions. |
| 2 | `evidence_based_tretment.pdf` | 62.33% | In adults with moderate-to-severe depression, citalopram, escitalopram, fluoxetine, fluvoxamine, paroxetine or sertraline (SSRIs) or amitriptyline (TCA) should be considered. |
| 3 | `mhgap.pdf` | 62.33% | In adults with moderate-to-severe depression, citalopram, escitalopram, fluoxetine, fluvoxamine, paroxetine or sertraline (SSRIs) or amitriptyline (TCA) should be considered. |
