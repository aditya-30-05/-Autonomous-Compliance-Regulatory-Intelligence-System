"""
agents/explainer.py
─────────────────────────────────────────────────────────────────────────────
Explainable AI Layer — Provides human-readable explanations for:
  1. Why a policy was matched (transparency)
  2. "Explain in Simple Terms" for any regulatory change
  3. Risk reasoning visibility

Input  : state dict with changes, mappings
Output : enriches mappings with 'match_explanation' and provides
         on-demand /summary endpoint support.
─────────────────────────────────────────────────────────────────────────────
"""

from typing import Any
from utils.llm_client import get_llm_client, build_prompt

# ── Match Explanation Prompt ──────────────────────────────────────────────────

EXPLAIN_MATCH_PROMPT = """\
You are explaining to a compliance officer why an AI system matched a \
regulatory change to a specific internal policy.

### Regulatory Change:
Section  : {section}
Change   : {summary}
Keywords : {keywords}

### Matched Policy:
Title   : {policy_title}
ID      : {policy_id}
Excerpt : {excerpt}
Match Score: {score}

### Task:
In 1-2 sentences, explain clearly why this policy was selected as a match.
Mention specific overlapping topics, keywords, or regulatory areas.
Start with "This policy was selected because..."
"""

# ── Simple Summary Prompt ─────────────────────────────────────────────────────

SIMPLE_SUMMARY_PROMPT = """\
You are explaining a regulatory change to a non-technical business stakeholder.

### Regulatory Change:
Type    : {change_type}
Section : {section}
Risk    : {risk}
Details : {details}

### Task:
Explain this change in 2-3 simple sentences that anyone can understand.
Avoid legal jargon. Focus on: what changed, why it matters, and what
the company needs to do. Use everyday language.
"""


def _extract_keywords(text: str) -> str:
    """Extract salient keywords from text for explanation."""
    import re
    words = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', text)
    # Also grab known financial terms
    financial = [
        "capital", "CAR", "CET1", "KYC", "AML", "NPA", "LCR",
        "IRRBB", "RWA", "leverage", "provisioning", "reporting",
        "disclosure", "EVE", "Basel", "D-SIB",
    ]
    text_lower = text.lower()
    matched = [kw for kw in financial if kw.lower() in text_lower]
    combined = list(set(words[:8] + matched))[:10]
    return ", ".join(combined) if combined else "general regulatory"


# ── Public API ────────────────────────────────────────────────────────────────

def enrich_mappings(state: dict[str, Any]) -> dict[str, Any]:
    """
    Add 'match_explanation' to each policy in each mapping.
    Also adds 'confidence_pct' as a human-readable percentage.
    """
    mappings: list[dict] = state.get("mappings", [])
    if not mappings:
        return state

    llm = get_llm_client()

    for mapping in mappings:
        change = mapping.get("change", {})
        keywords = _extract_keywords(" ".join(filter(None, [
            change.get("summary", ""),
            change.get("new", ""),
        ])))

        for policy in mapping.get("matched_policies", []):
            # Add confidence percentage
            raw_score = policy.get("score", 0)
            policy["confidence_pct"] = round(raw_score * 100, 1)

            prompt = build_prompt(EXPLAIN_MATCH_PROMPT, {
                "section":      change.get("section", ""),
                "summary":      change.get("summary", "")[:200],
                "keywords":     keywords,
                "policy_title": policy["policy_title"],
                "policy_id":    policy["policy_id"],
                "excerpt":      policy.get("excerpt", "")[:200],
                "score":        policy["confidence_pct"],
            })

            try:
                result = llm.invoke(prompt)
                explanation = result.content if hasattr(result, "content") else str(result)
            except Exception:
                explanation = (
                    f"This policy was selected because it shares regulatory topics "
                    f"related to {keywords} with a confidence of {policy['confidence_pct']}%."
                )
            policy["match_explanation"] = explanation.strip()

    print(f"[Explainer] ✅  Added explanations to {len(mappings)} mapping(s)")
    return {**state, "mappings": mappings}


def generate_simple_summary(change: dict) -> str:
    """
    Generate an 'Explain in Simple Terms' summary for a single change.
    Called by the /summary API endpoint.
    """
    llm = get_llm_client()
    details = " ".join(filter(None, [
        change.get("summary", ""),
        change.get("new", ""),
        change.get("old", ""),
    ]))[:500]

    prompt = build_prompt(SIMPLE_SUMMARY_PROMPT, {
        "change_type": change.get("type", "MODIFIED"),
        "section":     change.get("section", "General"),
        "risk":        change.get("risk", "MEDIUM"),
        "details":     details,
    })

    try:
        result = llm.invoke(prompt)
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        return f"Summary unavailable ({e}). Please review the original change details."
