# Mental Health Care

An AI-powered mental health screening and support platform with RAG (Retrieval-Augmented Generation), longitudinal patient tracking, and privacy-first clinical workflows.

## Prerequisites

- **Python 3.12+**
- **Node.js 18+** (with npm)
- **PostgreSQL 14+**
- **Ollama** (for local LLM inference)
- **CUDA GPU** (16+ GB VRAM, required only for fine-tuning)

## Quick Start

### 1. Clone and set up Python environment

```bash
git clone <repo-url>
cd Mental_health_issues

python -m venv mhi
mhi\Scripts\activate        # Windows
# source mhi/bin/activate   # Linux/Mac

pip install -r requirements.txt
```

### 2. Configure environment

Copy the example env file and fill in your values:

```bash
copy .env.example .env
```

Edit `.env` and set at minimum:
- `MHC_DATABASE_URL` — your PostgreSQL connection string
- `MHC_JWT_SECRET` — a long random string for JWT signing
- `MHC_FIELD_ENCRYPTION_KEY` — generate with:
  ```bash
  python -c "from app.security.encryption import generate_key; print(generate_key())"
  ```

### 3. Set up PostgreSQL

Using pgAdmin or `psql`:

```sql
CREATE DATABASE mhcare;
```

Then initialize the schema:

```bash
python scripts/initialize_db.py --sql
```

This creates all tables defined in `database/schema.sql`.

### 4. Install and start Ollama

Download from [ollama.ai](https://ollama.ai), then pull the required models:

```bash
ollama pull llama3
ollama serve
```

### 5. Build the RAG vector store

Place your PDF documents in `datasets/`, then build embeddings:

```bash
python -m ml_ai.rag.embeddings.generation
```

This creates a ChromaDB vector store at `datasets/chroma_db/`.

### 6. Start the backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000/api/v1/`.

### 7. Start the frontend

```bash
cd frontend/web
npm install
npm run dev
```

The app is available at `http://localhost:5173/`.

---

## Training Environment (Separate venv)

Training and fine-tuning require GPU-dependent packages (`bitsandbytes`, `accelerate`, `trl`) that conflict with the CPU-only inference environment. Use a **separate venv** for all training work.

### Setup

```bash
python -m venv mhi-train
mhi-train\Scripts\activate        # Windows
# source mhi-train/bin/activate   # Linux/Mac

pip install -r requirements-train.txt
```

`requirements-train.txt` inherits all main dependencies and adds GPU-specific packages.

### `.env` variables required for training

The training environment reads the same `.env` file. These variables must be set:

| Variable | Required | Description |
|----------|----------|-------------|
| `HF_TOKEN` | **Yes** | Hugging Face token for downloading `unsloth/Llama-3.2-3B-Instruct-bnb-4bit` |
| `TORCH_DEVICE` | No | Set to `cuda` for GPU training (default: `cpu`) |
| `EMBEDDING_DEVICE` | No | Keep as `cpu` (embedding model always runs on CPU) |

Set your Hugging Face token before training:

```bash
# Windows
set HF_TOKEN=your_hf_token_here

# Linux/Mac
export HF_TOKEN=your_hf_token_here
```

Get your token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

### When to use each environment

| Task | Environment |
|------|-------------|
| Running the backend server | `mhi` |
| Building the RAG vector store | `mhi` |
| All inference and serving | `mhi` |
| Fine-tuning the LLM | `mhi-train` |
| Merging LoRA adapters | `mhi-train` |
| Training the longitudinal classifier | `mhi-train` |

---

## Fine-Tuning the LLM

The project uses a fine-tuned Llama 3.2 3B model for mental health conversations. To retrain:

### Requirements
- CUDA GPU with 16+ GB VRAM
- Hugging Face account and token
- **Training environment** (see above)

### Steps

1. Activate the training environment:
   ```bash
   mhi-train\Scripts\activate
   ```

2. Set your Hugging Face token:
   ```bash
   set HF_TOKEN=your_token_here
   ```

3. Run fine-tuning (QLoRA, ~4-bit quantized):
   ```bash
   python -m ml_ai.prompts.finetuning --epochs 3 --max-samples 500
   ```

4. The fine-tuned model is saved to `ml_ai/prompts/llama-3.2-3b-mental-health-screening/`.

5. Merge LoRA adapters into the base model:
   ```bash
   python -m ml_ai.prompts.merge_adapter
   ```

### Training configuration
- **Base model:** `unsloth/Llama-3.2-3B-Instruct-bnb-4bit`
- **Method:** QLoRA (4-bit quantization + LoRA adapters)
- **Default output:** `ml_ai/prompts/llama-3.2-3b-mental-health-screening/`

## Training ML Models

The longitudinal classifier tracks patient progress over time using TF-IDF + SVM:

```bash
# Activate training environment first
mhi-train\Scripts\activate

python -m ml_ai.longitudinal.baseline
```

This trains a baseline classifier on labeled mental health data and saves models to `ml_ai/prediction/models/baseline/`.

---

## Project Structure

```
Mental_health_issues/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/                # API route handlers
│   │   ├── core/               # Config, database, settings
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── security/           # Auth, encryption, RBAC
│   │   ├── services/           # Business logic layer
│   │   └── workers/            # Background jobs
│   └── tests/                  # Test suite
├── ml_ai/                      # ML/AI pipeline
│   ├── chat/                   # LangGraph conversational agent
│   ├── longitudinal/           # Patient progress tracking
│   ├── prompts/                # LLM fine-tuning & inference
│   └── rag/                    # Retrieval-Augmented Generation
│       ├── embeddings/         # ChromaDB vector store
│       ├── ingestion/          # PDF loading & chunking
│       └── vectorstore/        # Vector store client
├── clinical/                   # Clinical screening instruments
│   ├── clinical_registry/      # Condition & screening YAML configs
│   ├── screening/              # PHQ-9, GAD-7, C-SSRS, etc.
│   └── documentation/          # Clinical reference docs
├── datasets/                   # RAG documents & vector store
│   ├── chroma_db/              # ChromaDB database (git-ignored)
│   └── *.pdf                   # Source documents (git-ignored)
├── database/
│   └── schema.sql              # PostgreSQL DDL
├── frontend/
│   └── web/                    # React + TypeScript + Vite
├── scripts/
│   └── initialize_db.py        # DB setup utility
├── docs/
│   └── privacy_governance.md   # Privacy implementation guide
├── requirements.txt            # Main dependencies (inference)
├── requirements-train.txt      # Training dependencies (GPU)
├── .env.example                # Environment variable template
└── README.md
```

## Environment Variables

### Main application (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MHC_DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/mhcare` | PostgreSQL connection string |
| `MHC_JWT_SECRET` | — | Secret key for JWT signing |
| `MHC_JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `MHC_ACCESS_TOKEN_TTL_MINUTES` | `30` | Access token lifetime |
| `MHC_FIELD_ENCRYPTION_KEY` | — | Fernet key for encrypting health data |
| `MHC_DATA_RESIDENCY_REGION` | `in` | Data residency region (India) |
| `MHC_ALLOWED_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | CORS allowed origins |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `EMBEDDING_DEVICE` | `cpu` | Device for embedding model |
| `TORCH_DEVICE` | `cpu` | PyTorch device for ML models |
| `HF_TOKEN` | — | Hugging Face token (for fine-tuning only) |

### Training environment (additional)

| Variable | Required | Description |
|----------|----------|-------------|
| `HF_TOKEN` | **Yes** | Hugging Face token for model downloads |
| `TORCH_DEVICE` | Recommended | Set to `cuda` for GPU training |

## API Endpoints

| Prefix | Description |
|--------|-------------|
| `/api/v1/auth` | Registration, login, token refresh |
| `/api/v1/chat` | Conversational AI screening |
| `/api/v1/assessments` | Screening assessment CRUD |
| `/api/v1/consent` | Patient consent management |
| `/api/v1/users` | User profile management |
| `/api/v1/admin` | Admin operations |
| `/api/v1/audit` | Audit log access |
| `/health` | Health check |

## License

Proprietary. All rights reserved.
