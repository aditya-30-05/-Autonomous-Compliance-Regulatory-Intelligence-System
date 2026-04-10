"""
agents/drafter.py
─────────────────────────────────────────────────────────────────────────────
Drafter Agent — Generates suggested policy update language for each mapped
regulatory change using an LLM.

Input  (JSON): { "mappings": [ MappingItem ] }
Output (JSON): { "drafts":   [ DraftItem ] }

DraftItem = {
    "change_summary": str,
    "policy_id":      str,
    "policy_title":   str,
    "draft_update":   str,
    "rationale":      str,
    "risk":           str
}
─────────────────────────────────────────────────────────────────────────────
"""

from typing import Any
from utils.llm_client import get_llm_client, build_prompt

# ── Prompt templates ──────────────────────────────────────────────────────────

DRAFT_PROMPT = """\
You are a senior legal & compliance writer at a financial institution in India.

### Regulatory Change:
Type    : {change_type}
Section : {section}
Risk    : {risk}
Summary : {summary}

### Existing Policy to Update:
Policy ID    : {policy_id}
Policy Title : {policy_title}
Current Text : {policy_excerpt}

### Mapping Analysis:
{llm_analysis}

### Your Task:
1. Write a concise, professional UPDATE to the existing policy that:
   - Addresses the regulatory change
   - Uses clear, unambiguous legal language
   - Maintains the original policy's structure
2. State a one-sentence rationale for the change.

### Response Format:
DRAFT UPDATE:
<updated policy clause text here>

RATIONALE:
<one-sentence rationale>
"""

NO_POLICY_PROMPT = """\
You are a compliance officer at an Indian financial institution.

### Regulatory Change:
Type    : {change_type}
Section : {section}
Risk    : {risk}
Summary : {summary}
Detail  : {new_text}

### Task:
No existing internal policy was found for this regulation.
Draft a NEW policy clause that:
- Directly addresses this regulatory requirement
- Is concise, formal, and enforceable
- Would be appropriate for an RBI/SEBI-regulated entity

### Response Format:
DRAFT UPDATE:
<new policy clause>

RATIONALE:
<one-sentence rationale>
"""


def _parse_draft_response(raw: str) -> tuple[str, str]:
    """Extract DRAFT UPDATE and RATIONALE from LLM response."""
    draft = ""
    rationale = ""

    if "DRAFT UPDATE:" in raw:
        parts = raw.split("DRAFT UPDATE:")
        after = parts[1] if len(parts) > 1 else ""
        if "RATIONALE:" in after:
            draft_part, rat_part = after.split("RATIONALE:", 1)
            draft = draft_part.strip()
            rationale = rat_part.strip()
        else:
            draft = after.strip()
    else:
        draft = raw.strip()

    return draft or raw.strip(), rationale or "No rationale provided."


# ── Public API ────────────────────────────────────────────────────────────────

def run(state: dict[str, Any]) -> dict[str, Any]:
    """
    Drafter Agent entry-point.

    State keys consumed
    -------------------
    mappings : list[dict]  — produced by MapperAgent
    """
    mappings: list[dict] = state.get("mappings", [])

    if not mappings:
        print("[DrafterAgent] ⚠️  No mappings to draft from.")
        return {**state, "drafts": []}

    llm = get_llm_client()
    drafts: list[dict] = []

    for mapping in mappings:
        change           = mapping.get("change", {})
        matched_policies = mapping.get("matched_policies", [])
        analysis         = mapping.get("llm_analysis", "")

        change_type = change.get("type", "MODIFIED")
        section     = change.get("section", "General")
        risk        = change.get("risk", "MEDIUM")
        summary     = change.get("summary", "")
        new_text    = change.get("new", "") or ""

        if matched_policies:
            # Draft update for each matched policy (take top 2 max)
            for policy in matched_policies[:2]:
                prompt = build_prompt(DRAFT_PROMPT, {
                    "change_type":    change_type,
                    "section":        section,
                    "risk":           risk,
                    "summary":        summary,
                    "policy_id":      policy["policy_id"],
                    "policy_title":   policy["policy_title"],
                    "policy_excerpt": policy["excerpt"][:400],
                    "llm_analysis":   analysis[:400],
                })

                try:
                    raw = llm.invoke(prompt)
                    raw = raw.content if hasattr(raw, "content") else str(raw)
                except Exception as e:
                    raw = f"DRAFT UPDATE:\n[LLM unavailable: {e}]\n\nRATIONALE:\nManual review required."

                draft_text, rationale = _parse_draft_response(raw)

                drafts.append({
                    "change_summary": summary,
                    "policy_id":      policy["policy_id"],
                    "policy_title":   policy["policy_title"],
                    "draft_update":   draft_text,
                    "rationale":      rationale,
                    "risk":           risk,
                })
        else:
            # No matching policy — draft a new clause
            prompt = build_prompt(NO_POLICY_PROMPT, {
                "change_type": change_type,
                "section":     section,
                "risk":        risk,
                "summary":     summary,
                "new_text":    new_text[:400],
            })

            try:
                raw = llm.invoke(prompt)
                raw = raw.content if hasattr(raw, "content") else str(raw)
            except Exception as e:
                raw = f"DRAFT UPDATE:\n[LLM unavailable: {e}]\n\nRATIONALE:\nManual review required."

            draft_text, rationale = _parse_draft_response(raw)

            drafts.append({
                "change_summary": summary,
                "policy_id":      "NEW",
                "policy_title":   f"New Policy — {section}",
                "draft_update":   draft_text,
                "rationale":      rationale,
                "risk":           risk,
            })

    print(f"[DrafterAgent] ✅  Generated {len(drafts)} draft update(s).")
    return {**state, "drafts": drafts}
