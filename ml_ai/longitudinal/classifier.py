from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = SCRIPT_DIR.parents[1] / "datasets" / "research_data" / "mental_health_unbanlanced.csv"
CACHE_PATH = SCRIPT_DIR / "mental_health_classifier.joblib"

_model = None


def _build_model():
    """Train the classifier once and return the fitted pipeline."""
    print("Training mental-health classifier...")

    data = pd.read_csv(CSV_PATH)
    X_train, _, y_train, _ = train_test_split(
        data["text"],
        data["status"],
        test_size=0.2,
        random_state=42,
    )

    pipe = make_pipeline(
        TfidfVectorizer(
            ngram_range=(1, 3),
            sublinear_tf=True,
            min_df=3,
            max_df=0.9,
        ),
        LinearSVC(
            class_weight="balanced",
            random_state=42,
        ),
    )
    pipe.fit(X_train, y_train)

    return pipe


def load_classifier(force_retrain: bool = False):
    """Load the fitted classifier into memory.

    The original implementation retrained the SVM the first time classify()
    was called. The fitted pipeline is now persisted with joblib so server
    restarts do not retrain it unless the source CSV changed.
    """
    global _model

    if _model is not None and not force_retrain:
        return _model

    source_mtime = CSV_PATH.stat().st_mtime

    if (
        not force_retrain
        and CACHE_PATH.exists()
    ):
        try:
            cached = joblib.load(CACHE_PATH)

            if cached.get("source_mtime") == source_mtime:
                _model = cached["model"]
                print("Mental-health classifier loaded from cache.")
                return _model

            print("Classifier dataset changed; retraining...")
        except Exception as exc:
            print(f"Could not load classifier cache: {exc}")
            print("Retraining classifier...")

    _model = _build_model()

    joblib.dump(
        {
            "source_mtime": source_mtime,
            "model": _model,
        },
        CACHE_PATH,
        compress=3,
    )

    print(f"Classifier cached at: {CACHE_PATH}")
    return _model


def preload():
    """Load the classifier into memory at startup."""
    load_classifier()


def classify(text: str) -> str:
    """Classify using the already-loaded classifier."""
    model = load_classifier()
    prediction = model.predict([text])[0]
    return str(prediction)
