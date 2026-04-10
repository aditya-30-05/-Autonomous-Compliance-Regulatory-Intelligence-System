"""
agents/diff.py
─────────────────────────────────────────────────────────────────────────────
Diff Agent — Detects changes between an OLD and a NEW regulatory document.

Input  (JSON): { "full_text": str,            ← new document (from parser)
                 "old_text":  str  (optional)  ← previous version text }
Output (JSON): { "changes": [ ChangeItem ] }

ChangeItem = {
    "type":    "ADDED" | "REMOVED" | "MODIFIED",
    "section": str,
    "old":     str | None,
    "new":     str | None,
    "risk":    "HIGH" | "MEDIUM" | "LOW"
}
─────────────────────────────────────────────────────────────────────────────
"""

import difflib
import re
from typing import Any

# ── Risk heuristics ──────────────────────────────────────────────────────────
HIGH_RISK_KEYWORDS = [
    "mandatory", "penalty", "prohibited", "immediately", "deadline",
    "non-compliance", "suspension", "revoked", "cease", "criminal",
    "strict", "enforcement", "failure to comply", "interest rate",
]
MEDIUM_RISK_KEYWORDS = [
    "amendment", "revised", "updated", "modified", "new requirement",
    "reporting", "disclosure", "threshold", "limit", "capital",
]


def _risk_level(text: str) -> str:
    t = text.lower()
    if any(kw in t for kw in HIGH_RISK_KEYWORDS):
        return "HIGH"
    if any(kw in t for kw in MEDIUM_RISK_KEYWORDS):
        return "MEDIUM"
    return "LOW"


def _sentence_split(text: str) -> list[str]:
    """Split text into sentence-level lines for fine-grained diff."""
    # Split on sentence boundaries, keep non-empty lines
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def _infer_section(line: str, context_lines: list[str]) -> str:
    """
    Very lightweight section detector:
    walk backwards through context_lines looking for an all-caps heading.
    """
    for ctx in reversed(context_lines):
        if re.match(r"^[A-Z][A-Z\s\d\-:]{4,}$", ctx.strip()):
            return ctx.strip()
    return "General"


# ── Public API ────────────────────────────────────────────────────────────────

def run(state: dict[str, Any]) -> dict[str, Any]:
    """
    Diff Agent entry-point.

    State keys consumed
    -------------------
    full_text : str  — new document text (produced by ParserAgent)
    old_text  : str  — previous version text (empty string if first upload)
    """
    new_text: str = state.get("full_text", "")
    old_text: str = state.get("old_text", "")

    if not old_text.strip():
        # No previous version → treat all content as NEW
        print("[DiffAgent] ⚠️  No previous version supplied – marking all as ADDED")
        changes = [{
            "type": "ADDED",
            "section": "Full Document",
            "old": None,
            "new": new_text[:500] + "…",
            "risk": "MEDIUM",
            "summary": "First upload – no baseline document for comparison.",
        }]
        return {**state, "changes": changes}

    old_lines = _sentence_split(old_text)
    new_lines = _sentence_split(new_text)

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    opcodes = matcher.get_opcodes()

    changes: list[dict] = []

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            continue

        old_snippet = " ".join(old_lines[i1:i2])
        new_snippet = " ".join(new_lines[j1:j2])

        # Determine change type
        if tag == "insert":
            change_type = "ADDED"
            risk_text = new_snippet
        elif tag == "delete":
            change_type = "REMOVED"
            risk_text = old_snippet
        else:  # replace
            change_type = "MODIFIED"
            risk_text = old_snippet + " " + new_snippet

        section = _infer_section(
            new_lines[j1] if j1 < len(new_lines) else old_lines[i1],
            new_lines[:j1] if j1 > 0 else old_lines[:i1],
        )

        risk = _risk_level(risk_text)

        changes.append({
            "type": change_type,
            "section": section,
            "old": old_snippet[:400] if old_snippet else None,
            "new": new_snippet[:400] if new_snippet else None,
            "risk": risk,
            "summary": (
                f"{change_type} in '{section}': "
                + (new_snippet[:120] if new_snippet else old_snippet[:120])
            ),
        })

    # Sort: HIGH first, then MEDIUM, then LOW
    priority = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    changes.sort(key=lambda c: priority[c["risk"]])

    print(f"[DiffAgent] ✅  {len(changes)} change(s) detected "
          f"(HIGH:{sum(1 for c in changes if c['risk']=='HIGH')}, "
          f"MEDIUM:{sum(1 for c in changes if c['risk']=='MEDIUM')}, "
          f"LOW:{sum(1 for c in changes if c['risk']=='LOW')})")

    return {**state, "changes": changes}
