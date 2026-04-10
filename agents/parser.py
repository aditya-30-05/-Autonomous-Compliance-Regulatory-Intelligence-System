"""
agents/parser.py
─────────────────────────────────────────────────────────────────────────────
Parser Agent — Extracts and cleans text from regulatory PDF documents.

Input  (JSON): { "file_path": str }
Output (JSON): { "chunks": [str], "full_text": str, "metadata": {...} }
─────────────────────────────────────────────────────────────────────────────
"""

import os
import re
from typing import Any

import fitz  # PyMuPDF

# ── Config ────────────────────────────────────────────────────────────────────
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 700))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 100))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Remove excess whitespace, page numbers, and ligature artifacts."""
    text = re.sub(r"\f", "\n", text)                    # form‑feeds → newlines
    text = re.sub(r"[ \t]+", " ", text)                 # collapse spaces/tabs
    text = re.sub(r"\n{3,}", "\n\n", text)              # collapse blank lines
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)        # lone page numbers
    return text.strip()


def _word_count(text: str) -> int:
    return len(text.split())


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
                overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping word‑level chunks.
    chunk_size / overlap are expressed in *words* (≈ tokens for English text).
    """
    words = text.split()
    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap  # slide forward with overlap

    return chunks


# ── Public API ────────────────────────────────────────────────────────────────

def run(state: dict[str, Any]) -> dict[str, Any]:
    """
    Parser Agent entry‑point.

    Expected state keys
    -------------------
    file_path : str  — absolute / relative path to the regulatory PDF
    """
    file_path: str = state.get("file_path", "")

    if not file_path or not os.path.exists(file_path):
        return {
            **state,
            "error": f"Parser Agent: file not found → '{file_path}'",
        }

    doc = fitz.open(file_path)

    # Extract raw text page by page
    raw_pages: list[str] = [page.get_text("text") for page in doc]
    doc.close()

    full_raw = "\n\n".join(raw_pages)
    full_text = _clean_text(full_raw)
    chunks = _chunk_text(full_text)

    metadata = {
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "page_count": len(raw_pages),
        "word_count": _word_count(full_text),
        "chunk_count": len(chunks),
    }

    print(f"[ParserAgent] ✅  Extracted {metadata['word_count']} words "
          f"→ {metadata['chunk_count']} chunks from '{metadata['file_name']}'")

    return {
        **state,
        "full_text": full_text,
        "chunks": chunks,
        "doc_metadata": metadata,
    }
