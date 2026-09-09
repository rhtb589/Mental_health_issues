"""PDF text extraction for RAG ingestion pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Generator

from pypdf import PdfReader


class PDFLoader:
    """Extract text page-by-page from PDF files."""

    def __init__(self, min_page_chars: int = 10):
        self.min_page_chars = min_page_chars

    def load(self, pdf_path: Path) -> Generator[dict, None, None]:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        reader = PdfReader(str(pdf_path))
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and len(text.strip()) >= self.min_page_chars:
                yield {
                    "text": text.strip(),
                    "source": pdf_path.name,
                    "page": i + 1,
                    "doc_type": "pdf",
                }
