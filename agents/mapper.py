"""
agents/mapper.py
─────────────────────────────────────────────────────────────────────────────
Mapping Agent (RAG-based) — Matches detected regulatory changes to internal
company policies stored in ChromaDB.

Input  (JSON): { "changes": [ ChangeItem ] }
Output (JSON): { "mappings": [ MappingItem ] }

MappingItem = {
    "change":           ChangeItem,
    "matched_policies": [ PolicyMatch ],
    "llm_analysis":     str
}
PolicyMatch = {
    "policy_id":    str,
    "policy_title": str,
    "excerpt":      str,
    "score":        float
}
─────────────────────────────────────────────────────────────────────────────
"""

import os
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from utils.llm_client import get_llm_client, build_prompt

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./db/chroma_store")
COLLECTION  = os.getenv("CHROMA_COLLECTION_NAME", "company_policies")
TOP_K       = int(os.getenv("TOP_K_RESULTS", 5))


# ── ChromaDB helpers ──────────────────────────────────────────────────────────

def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    emb_fn = embedding_functions.DefaultEmbeddingFunction()
    return client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=emb_fn,
    )


def _search_policies(query: str, top_k: int = TOP_K) -> list[dict]:
    collection = _get_collection()

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    matches = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            matches.append({
                "policy_id":    meta.get("policy_id", "UNKNOWN"),
                "policy_title": meta.get("policy_title", "Unnamed Policy"),
                "excerpt":      doc[:300],
                "score":        round(1 - dist, 4),  # cosine similarity proxy
            })
    return matches


# ── LLM analysis ─────────────────────────────────────────────────────────────
MAPPING_PROMPT = """\
You are a regulatory compliance analyst.

### Regulatory Change Detected:
Type     : {change_type}
Section  : {section}
Risk     : {risk}
Old Text : {old}
New Text : {new}

### Matched Internal Policies:
{policies}

### Task:
1. Briefly explain how this regulatory change impacts each matched policy.
2. Identify which policy clauses need to be updated.
3. Assign an overall impact score: HIGH / MEDIUM / LOW.

Respond in 3–5 concise sentences.
"""


def _format_policies(matches: list[dict]) -> str:
    if not matches:
        return "No matching policies found."
    lines = []
    for m in matches:
        lines.append(
            f"  [{m['policy_id']}] {m['policy_title']} (score: {m['score']})\n"
            f"  Excerpt: {m['excerpt'][:200]}"
        )
    return "\n\n".join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def run(state: dict[str, Any]) -> dict[str, Any]:
    """
    Mapping Agent entry-point.

    State keys consumed
    -------------------
    changes : list[dict]  — produced by DiffAgent
    """
    changes: list[dict] = state.get("changes", [])

    if not changes:
        print("[MapperAgent] ⚠️  No changes to map.")
        return {**state, "mappings": []}

    llm = get_llm_client()
    mappings: list[dict] = []

    for change in changes:
        query = " ".join(filter(None, [
            change.get("summary", ""),
            change.get("new", ""),
            change.get("old", ""),
        ]))[:600]

        matched = _search_policies(query)

        prompt = build_prompt(MAPPING_PROMPT, {
            "change_type": change.get("type", ""),
            "section":     change.get("section", ""),
            "risk":        change.get("risk", ""),
            "old":         change.get("old") or "N/A",
            "new":         change.get("new") or "N/A",
            "policies":    _format_policies(matched),
        })

        try:
            analysis = llm.invoke(prompt)
            if hasattr(analysis, "content"):
                analysis = analysis.content
        except Exception as e:
            analysis = f"[LLM unavailable] {str(e)}"

        mappings.append({
            "change":           change,
            "matched_policies": matched,
            "llm_analysis":     str(analysis),
        })

    print(f"[MapperAgent] ✅  Mapped {len(mappings)} change(s) to internal policies.")
    return {**state, "mappings": mappings}
