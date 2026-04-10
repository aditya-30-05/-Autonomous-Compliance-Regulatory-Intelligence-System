"""
api/main.py
─────────────────────────────────────────────────────────────────────────────
FastAPI backend — REST API layer for the Compliance Intelligence System.

Endpoints:
  POST /upload            — Upload new (and optionally old) PDF
  POST /run               — Trigger the full agent pipeline
  GET  /report            — Retrieve the latest HTML report
  GET  /report/json       — Retrieve the latest JSON report summary
  GET  /report/download   — Download HTML report file
  POST /risk-score        — Get risk breakdown for a specific change
  POST /summary           — "Explain in Simple Terms" for a change
  GET  /deadlines         — Get all extracted deadlines
  GET  /policies/load     — Re-ingest policy documents into ChromaDB
  GET  /health            — Health check
  GET  /sessions/{id}     — Get session status
─────────────────────────────────────────────────────────────────────────────
"""

import json
import os
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

# Internal modules
from orchestrator.workflow import run_pipeline
from utils.policy_loader import load_policies
from agents.explainer import generate_simple_summary

# ── Dirs ───────────────────────────────────────────────────────────────────────
UPLOAD_DIR  = Path(os.getenv("UPLOAD_DIR",  "./data/uploads"))
REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "./data/reports"))

for d in [UPLOAD_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Autonomous Compliance & Regulatory Intelligence System",
    description="Multi-agent AI system for regulatory change detection, policy mapping, risk scoring, and compliance reporting.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

# Database session interface
from api import db



# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_upload(file: UploadFile, prefix: str) -> Path:
    suffix = Path(file.filename).suffix or ".pdf"
    dest = UPLOAD_DIR / f"{prefix}_{uuid.uuid4().hex}{suffix}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return dest


def _latest_report(ext: str) -> Optional[Path]:
    files = sorted(REPORTS_DIR.glob(f"report_*.{ext}"), reverse=True)
    return files[0] if files else None


def _get_session_result(session_id: str) -> dict:
    """Get session result, raise 404 if not found or no result."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    result = session.get("result")
    if not result:
        raise HTTPException(400, "Pipeline has not been run yet for this session.")
    return result


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ComplianceAI",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "agents": [
            "parser", "diff", "risk_scorer", "mapper",
            "explainer", "drafter", "deadline_tracker", "reporter"
        ],
    }


@app.post("/upload", summary="Upload regulatory PDF(s)")
async def upload(
    new_pdf: UploadFile = File(..., description="New regulatory circular PDF"),
    old_pdf: Optional[UploadFile] = File(None, description="Previous version PDF (optional)"),
):
    """
    Upload one or two PDF files.
    Returns a session_id to pass to POST /run.
    """
    if not new_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")

    session_id = uuid.uuid4().hex
    new_path = _save_upload(new_pdf, "new")

    old_path = None
    if old_pdf and old_pdf.filename:
        old_path = _save_upload(old_pdf, "old")

    db.create_session(session_id, str(new_path), str(old_path) if old_path else None)

    return {
        "session_id": session_id,
        "new_file":   new_path.name,
        "old_file":   old_path.name if old_path else None,
        "message":    "Files uploaded. Call POST /run with this session_id.",
    }


@app.post("/run", summary="Trigger the compliance analysis pipeline")
async def run(session_id: str = Form(...)):
    """
    Runs the full multi-agent pipeline (8 agents) for the given session.
    Returns the JSON report summary immediately.
    """
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(404, f"Session '{session_id}' not found. Upload files first.")

    new_path = session["new_path"]
    old_path = session.get("old_path")

    # Read old text if a previous PDF was supplied
    old_text = ""
    if old_path and Path(old_path).exists():
        import fitz
        doc = fitz.open(old_path)
        old_text = "\n\n".join(page.get_text("text") for page in doc)
        doc.close()

    # Run orchestrator
    try:
        result = run_pipeline(file_path=new_path, old_text=old_text)
    except Exception as e:
        raise HTTPException(500, f"Pipeline error: {str(e)}")

    db.update_session_result(session_id, result)

    # Build enriched response
    report_json = result.get("report_json", {})
    return JSONResponse({
        "session_id":     session_id,
        "report_path":    result.get("report_path"),
        "stats":          report_json.get("stats", {}),
        "all_deadlines":  result.get("all_deadlines", []),
        "message":        "Pipeline complete (8 agents). Fetch full report via GET /report or /report/json",
    })


@app.get("/report", response_class=HTMLResponse, summary="Get latest HTML report")
async def get_report_html():
    """Returns the most recently generated HTML compliance report."""
    path = _latest_report("html")
    if not path:
        raise HTTPException(404, "No report found. Run the pipeline first.")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/report/json", summary="Get latest JSON report summary")
async def get_report_json():
    """Returns the most recently generated JSON compliance report."""
    path = _latest_report("json")
    if not path:
        raise HTTPException(404, "No JSON report found. Run the pipeline first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    return JSONResponse(data)


@app.get("/report/download", summary="Download latest HTML report file")
async def download_report():
    path = _latest_report("html")
    if not path:
        raise HTTPException(404, "No report found.")
    return FileResponse(str(path), media_type="text/html",
                        filename=path.name)


# ── NEW: Risk Score Endpoint ──────────────────────────────────────────────────

@app.post("/risk-score", summary="Get detailed risk breakdown for a change")
async def get_risk_score(change: dict = Body(...)):
    """
    Compute detailed risk score for a single change.
    Input: { "type": "MODIFIED", "section": "...", "old": "...", "new": "...", "summary": "..." }
    """
    from agents.risk_scorer import _compute_breakdown, _weighted_total, _level_from_score

    text = " ".join(filter(None, [
        change.get("summary", ""),
        change.get("old", ""),
        change.get("new", ""),
    ]))

    breakdown = _compute_breakdown(text)
    score = _weighted_total(breakdown)
    level = _level_from_score(score)

    return {
        "risk_score":     score,
        "risk_level":     level,
        "risk_breakdown": breakdown,
        "change_section": change.get("section", "General"),
    }


# ── NEW: Simple Summary Endpoint ─────────────────────────────────────────────

@app.post("/summary", summary="Explain a change in simple terms")
async def get_simple_summary(change: dict = Body(...)):
    """
    Generate an 'Explain in Simple Terms' plain-language summary.
    Input: { "type": "MODIFIED", "section": "...", "old": "...", "new": "...", "risk": "...", "summary": "..." }
    """
    try:
        summary = generate_simple_summary(change)
        return {"summary": summary, "section": change.get("section", ""), "status": "ok"}
    except Exception as e:
        return {"summary": f"Summary unavailable: {str(e)}", "status": "error"}


# ── NEW: Deadlines Endpoint ──────────────────────────────────────────────────

@app.get("/deadlines", summary="Get all extracted compliance deadlines")
async def get_deadlines(session_id: Optional[str] = None):
    """
    Returns all deadlines extracted from the last pipeline run.
    Optionally filter by session_id.
    """
    if session_id:
        result = _get_session_result(session_id)
        deadlines = result.get("all_deadlines", [])
    else:
        # Return from latest report JSON
        path = _latest_report("json")
        if not path:
            raise HTTPException(404, "No report found.")
        data = json.loads(path.read_text(encoding="utf-8"))
        deadlines = data.get("all_deadlines", [])

    return {"deadlines": deadlines, "count": len(deadlines)}


# ── Existing endpoints ────────────────────────────────────────────────────────

@app.get("/policies/load", summary="Load/reload policy documents into ChromaDB")
async def reload_policies(reset: bool = False):
    """
    Ingests all .txt files from the policies directory into ChromaDB.
    Pass ?reset=true to wipe and reload.
    """
    count = load_policies(reset=reset)
    return {"chunks_loaded": count, "reset": reset, "status": "ok"}


@app.get("/sessions/{session_id}", summary="Get session status")
async def get_session(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found.")

    result = session.get("result")
    return {
        "session_id":   session_id,
        "has_result":   result is not None,
        "new_file":     Path(session["new_path"]).name,
        "old_file":     Path(session["old_path"]).name if session.get("old_path") else None,
        "created_at":   session.get("created_at"),
        "completed_at": session.get("completed_at"),
        "stats":        result.get("report_json", {}).get("stats") if result else None,
        "deadlines":    len(result.get("all_deadlines", [])) if result else 0,
    }


# ── NEW: Ingestion Endpoint ───────────────────────────────────────────────────

@app.get("/ingest", summary="Run Ingestion Agent")
async def run_ingestion(source: str = "rbi"):
    """
    Run the ingestion agent to pull recent circulars from a source.
    Allowed sources: 'rbi', 'sebi'.
    """
    from agents.ingestion import run as run_ingest
    
    try:
        res = run_ingest({"source": source})
        return {
            "source": source,
            "pdf_links": res.get("pdf_links", []),
            "status": "ok"
        }
    except Exception as e:
        raise HTTPException(500, f"Ingestion error: {str(e)}")


# ── Dev runner ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
