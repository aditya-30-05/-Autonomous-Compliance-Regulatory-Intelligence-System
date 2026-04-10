# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# ── System deps (needed by PyMuPDF) ──────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps ───────────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Create runtime directories ────────────────────────────────────────────────
RUN mkdir -p data/uploads data/reports data/policies data/demo \
             db/chroma_store frontend

# ── Environment defaults (override via docker run -e or --env-file) ───────────
ENV LLM_PROVIDER=openai \
    OPENAI_MODEL=gpt-4o-mini \
    CHROMA_PERSIST_DIR=/app/db/chroma_store \
    CHROMA_COLLECTION_NAME=company_policies \
    UPLOAD_DIR=/app/data/uploads \
    REPORTS_DIR=/app/data/reports \
    POLICIES_DIR=/app/data/policies

# ── Expose API port ───────────────────────────────────────────────────────────
EXPOSE 8000

# ── Start command ─────────────────────────────────────────────────────────────
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
