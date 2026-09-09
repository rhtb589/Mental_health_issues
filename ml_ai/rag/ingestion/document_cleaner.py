"""Text cleaning utilities for RAG ingestion pipeline."""
from __future__ import annotations

import re
import unicodedata


def clean_text(text: str) -> str:
    """Normalize and clean extracted text."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text.strip()
