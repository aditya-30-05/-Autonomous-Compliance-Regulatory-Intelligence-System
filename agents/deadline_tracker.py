"""
agents/deadline_tracker.py
─────────────────────────────────────────────────────────────────────────────
Compliance Deadline Tracker — Extracts temporal references and deadlines
from regulatory changes and computes actionable countdown information.

Output per change (added to change dict):
    deadlines: [
        {
            "text":        str,   — original deadline phrase
            "days":        int,   — days from now / extracted number
            "due_date":    str,   — ISO date if computable
            "urgency":     str,   — CRITICAL | URGENT | NORMAL
            "description": str,   — human-readable summary
        }
    ]
─────────────────────────────────────────────────────────────────────────────
"""

import re
from datetime import datetime, timedelta
from typing import Any

# ── Patterns ──────────────────────────────────────────────────────────────────

# "within 30 days" / "within sixty (60) days"
WITHIN_PATTERN = re.compile(
    r"within\s+(\w+)\s*(?:\((\d+)\))?\s*days?",
    re.IGNORECASE,
)

# "by December 31, 2025" / "by 31 December 2025" / "by 31-12-2025"
BY_DATE_PATTERN = re.compile(
    r"by\s+(\d{1,2}[\s\-/]\w+[\s\-/]\d{4}|\w+\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)

# "effective from April 1, 2025" / "effective June 30, 2025"
EFFECTIVE_PATTERN = re.compile(
    r"effective\s+(?:from\s+)?(\d{1,2}[\s\-/]\w+[\s\-/]\d{4}|\w+\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)

# "before March 2025" / "not later than 30 June 2025"
BEFORE_PATTERN = re.compile(
    r"(?:before|not\s+later\s+than|on\s+or\s+before)\s+(\d{1,2}[\s\-/]\w+[\s\-/]\d{4}|\w+\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)

# "immediately"
IMMEDIATE_PATTERN = re.compile(
    r"\b(immediately|with\s+immediate\s+effect|forthwith)\b",
    re.IGNORECASE,
)

# Word-to-number for common cases
WORD_NUMS = {
    "seven": 7, "fourteen": 14, "fifteen": 15, "twenty": 20,
    "thirty": 30, "forty": 40, "forty-five": 45, "sixty": 60,
    "ninety": 90, "one hundred eighty": 180, "one hundred": 100,
}


def _word_to_num(word: str) -> int | None:
    """Convert number word to int."""
    w = word.strip().lower()
    if w.isdigit():
        return int(w)
    return WORD_NUMS.get(w)


def _parse_date_str(date_str: str) -> datetime | None:
    """Try to parse a date string."""
    date_str = date_str.strip().replace(",", "")
    formats = [
        "%d %B %Y", "%B %d %Y", "%d-%m-%Y", "%d/%m/%Y",
        "%d %b %Y", "%b %d %Y", "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _urgency_from_days(days: int) -> str:
    if days <= 7: return "CRITICAL"
    if days <= 30: return "URGENT"
    return "NORMAL"


def extract_deadlines(text: str) -> list[dict]:
    """Extract all deadlines from a text snippet."""
    deadlines = []
    now = datetime.now()

    # 1. "immediately"
    for m in IMMEDIATE_PATTERN.finditer(text):
        deadlines.append({
            "text": m.group(0),
            "days": 0,
            "due_date": now.strftime("%Y-%m-%d"),
            "urgency": "CRITICAL",
            "description": "Required with immediate effect",
        })

    # 2. "within N days"
    for m in WITHIN_PATTERN.finditer(text):
        word_val = m.group(1)
        paren_val = m.group(2)
        days = int(paren_val) if paren_val else _word_to_num(word_val)
        if days:
            due = now + timedelta(days=days)
            deadlines.append({
                "text": m.group(0),
                "days": days,
                "due_date": due.strftime("%Y-%m-%d"),
                "urgency": _urgency_from_days(days),
                "description": f"Compliance required within {days} days",
            })

    # 3. Specific dates
    for pattern, label in [
        (BY_DATE_PATTERN, "Compliance deadline"),
        (EFFECTIVE_PATTERN, "Effective date"),
        (BEFORE_PATTERN, "Must comply before"),
    ]:
        for m in pattern.finditer(text):
            dt = _parse_date_str(m.group(1))
            if dt:
                delta = (dt - now).days
                deadlines.append({
                    "text": m.group(0),
                    "days": max(0, delta),
                    "due_date": dt.strftime("%Y-%m-%d"),
                    "urgency": _urgency_from_days(max(0, delta)),
                    "description": f"{label}: {dt.strftime('%B %d, %Y')}",
                })

    return deadlines


# ── Public API ────────────────────────────────────────────────────────────────

def run(state: dict[str, Any]) -> dict[str, Any]:
    """
    Deadline Tracker entry-point.

    Enriches each change in state['changes'] with 'deadlines' list.
    Also builds a top-level 'all_deadlines' aggregation.
    """
    changes: list[dict] = state.get("changes", [])
    all_deadlines = []

    for change in changes:
        text = " ".join(filter(None, [
            change.get("summary", ""),
            change.get("old", ""),
            change.get("new", ""),
        ]))
        dl = extract_deadlines(text)
        change["deadlines"] = dl
        for d in dl:
            all_deadlines.append({
                **d,
                "section": change.get("section", "General"),
                "risk":    change.get("risk", "LOW"),
            })

    # Sort by urgency
    urgency_order = {"CRITICAL": 0, "URGENT": 1, "NORMAL": 2}
    all_deadlines.sort(key=lambda x: (urgency_order.get(x["urgency"], 3), x["days"]))

    print(f"[DeadlineTracker] ✅  Extracted {len(all_deadlines)} deadline(s)")
    return {**state, "all_deadlines": all_deadlines}
