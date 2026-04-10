"""
agents/risk_scorer.py
─────────────────────────────────────────────────────────────────────────────
Risk Scoring Engine — Assigns multi-dimensional risk scores to detected
regulatory changes using rule-based heuristics PLUS LLM reasoning.

Output per change:
    risk_score:     float (0-100)
    risk_level:     HIGH | MEDIUM | LOW
    risk_breakdown: { compliance, financial, operational, reputational }
    risk_reasoning: str (LLM explanation)
─────────────────────────────────────────────────────────────────────────────
"""

import re
from typing import Any

from utils.llm_client import get_llm_client, build_prompt

# ── Weight configuration ──────────────────────────────────────────────────────

DIMENSION_WEIGHTS = {
    "compliance":   0.35,
    "financial":    0.30,
    "operational":  0.20,
    "reputational": 0.15,
}

# ── Keyword banks per dimension ───────────────────────────────────────────────

COMPLIANCE_HIGH = [
    "mandatory", "prohibited", "non-compliance", "penalty", "cease",
    "revoke", "suspension", "criminal", "debarment", "violation",
    "immediately", "strict enforcement", "failure to comply",
]
COMPLIANCE_MED = [
    "requirement", "shall", "must", "obligatory", "compliance",
    "direction", "guideline", "circular", "notification",
]

FINANCIAL_HIGH = [
    "capital adequacy", "car", "cet1", "tier 1", "leverage ratio",
    "risk weight", "provisioning", "write-off", "npa", "exposure limit",
    "slr", "crr", "capital add-on",
]
FINANCIAL_MED = [
    "interest rate", "fee", "charge", "cost", "pricing", "threshold",
    "limit", "margin", "reserve", "buffer",
]

OPERATIONAL_HIGH = [
    "deadline", "immediately", "within 7 days", "reporting",
    "real-time", "system upgrade", "it infrastructure",
    "daily submission", "automated",
]
OPERATIONAL_MED = [
    "process", "procedure", "workflow", "training", "audit",
    "review", "assessment", "documentation", "quarterly",
]

REPUTATIONAL_HIGH = [
    "public disclosure", "customer impact", "media", "consumer complaint",
    "data breach", "privacy", "kyc", "anti-money laundering", "aml",
]
REPUTATIONAL_MED = [
    "transparency", "ethics", "governance", "board", "stakeholder",
    "trust", "reputation",
]


def _keyword_score(text: str, high_kw: list, med_kw: list) -> float:
    """Score 0-100 based on keyword matches."""
    t = text.lower()
    high_hits = sum(1 for kw in high_kw if kw in t)
    med_hits  = sum(1 for kw in med_kw if kw in t)

    score = min(100, high_hits * 25 + med_hits * 10)
    return max(10, score)  # Floor at 10


def _compute_breakdown(text: str) -> dict:
    """Compute per-dimension scores."""
    return {
        "compliance":   _keyword_score(text, COMPLIANCE_HIGH,  COMPLIANCE_MED),
        "financial":    _keyword_score(text, FINANCIAL_HIGH,    FINANCIAL_MED),
        "operational":  _keyword_score(text, OPERATIONAL_HIGH,  OPERATIONAL_MED),
        "reputational": _keyword_score(text, REPUTATIONAL_HIGH, REPUTATIONAL_MED),
    }


def _weighted_total(breakdown: dict) -> float:
    total = sum(breakdown[k] * DIMENSION_WEIGHTS[k] for k in DIMENSION_WEIGHTS)
    return round(total, 1)


def _level_from_score(score: float) -> str:
    if score >= 60: return "HIGH"
    if score >= 35: return "MEDIUM"
    return "LOW"


# ── LLM risk reasoning ───────────────────────────────────────────────────────

RISK_PROMPT = """\
You are a regulatory risk analyst at a major Indian financial institution.

### Regulatory Change:
Type    : {change_type}
Section : {section}
Old Text: {old}
New Text: {new}

### Computed Risk Score: {score}/100 ({level})
Breakdown: Compliance={compliance}, Financial={financial}, \
Operational={operational}, Reputational={reputational}

### Task:
In 2-3 sentences, explain WHY this change carries this risk level.
Focus on concrete impacts: capital requirements, deadlines, penalties,
process changes, or customer-facing effects. Be specific and direct.
"""


def _get_reasoning(change: dict, score: float, level: str,
                   breakdown: dict, llm) -> str:
    prompt = build_prompt(RISK_PROMPT, {
        "change_type":  change.get("type", ""),
        "section":      change.get("section", ""),
        "old":          (change.get("old") or "N/A")[:200],
        "new":          (change.get("new") or "N/A")[:200],
        "score":        score,
        "level":        level,
        "compliance":   breakdown["compliance"],
        "financial":    breakdown["financial"],
        "operational":  breakdown["operational"],
        "reputational": breakdown["reputational"],
    })
    try:
        result = llm.invoke(prompt)
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        return f"Risk analysis unavailable ({e}). Score based on keyword analysis."


# ── Public API ────────────────────────────────────────────────────────────────

def run(state: dict[str, Any]) -> dict[str, Any]:
    """
    Risk Scoring Engine entry-point.

    Enriches each change in state['changes'] with:
      risk_score, risk_level, risk_breakdown, risk_reasoning
    """
    changes: list[dict] = state.get("changes", [])
    if not changes:
        return state

    llm = get_llm_client()
    scored_changes = []

    for change in changes:
        text = " ".join(filter(None, [
            change.get("summary", ""),
            change.get("old", ""),
            change.get("new", ""),
        ]))

        breakdown = _compute_breakdown(text)
        score = _weighted_total(breakdown)
        level = _level_from_score(score)
        reasoning = _get_reasoning(change, score, level, breakdown, llm)

        scored_changes.append({
            **change,
            "risk":           level,  # override simple heuristic
            "risk_score":     score,
            "risk_breakdown": breakdown,
            "risk_reasoning": reasoning,
        })

    # Sort by score descending
    scored_changes.sort(key=lambda c: c["risk_score"], reverse=True)

    print(f"[RiskScorer] ✅  Scored {len(scored_changes)} change(s)")
    return {**state, "changes": scored_changes}
