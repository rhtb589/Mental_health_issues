"""FastAPI application entrypoint.

Wires the API routers and exposes the privacy/consent/retention/RBAC/audit
surface defined in the requirements document.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.api import auth, consent, assessments, admin, users, research, dashboard, audit, assignments, data_requests, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_secrets()

    if settings.environment == "dev":
        import app.models  # noqa: F401 – registers all models
        try:
            Base.metadata.create_all(engine)
        except Exception as exc:
            raise SystemExit(
                f"Cannot connect to PostgreSQL ({exc}). "
                "Ensure PostgreSQL is running and the database exists. "
                "See README Step 3."
            ) from exc

    import time

    print("\n========== PRELOADING MODELS ==========")
    total_start = time.perf_counter()

    t = time.perf_counter()
    try:
        from ml_ai.longitudinal.classifier import preload as preload_classifier
        preload_classifier()
    except Exception as exc:
        print(f"[1] Classifier: FAILED ({exc})")
    else:
        print(f"[1] Classifier:         {time.perf_counter() - t:.2f}s")

    t = time.perf_counter()
    try:
        from ml_ai.rag.retriever import preload as preload_retriever
        preload_retriever()
    except Exception as exc:
        print(f"[2] RAG: FAILED ({exc})")
    else:
        print(f"[2] RAG (embeddings):   {time.perf_counter() - t:.2f}s")

    t = time.perf_counter()
    try:
        from ml_ai.prompts.inference import preload as preload_llm
        preload_llm()
    except Exception as exc:
        print(f"[3] LLM: FAILED ({exc})")
    else:
        print(f"[3] LLM (Llama 3.2):    {time.perf_counter() - t:.2f}s")

    print(f"[TOTAL]                  {time.perf_counter() - total_start:.2f}s")
    print("========================================\n")

    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(consent.router, prefix=settings.api_prefix)
    app.include_router(assessments.router, prefix=settings.api_prefix)
    app.include_router(users.router, prefix=settings.api_prefix)
    app.include_router(admin.router, prefix=settings.api_prefix)
    app.include_router(research.router, prefix=settings.api_prefix)
    app.include_router(dashboard.router, prefix=settings.api_prefix)
    app.include_router(audit.router, prefix=settings.api_prefix)
    app.include_router(assignments.router, prefix=settings.api_prefix)
    app.include_router(data_requests.router, prefix=settings.api_prefix)
    app.include_router(chat.router, prefix=settings.api_prefix)

    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "data_residency": settings.data_residency_region}

    return app


app = create_app()
