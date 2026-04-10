"""
agents/reporter.py
─────────────────────────────────────────────────────────────────────────────
Report Agent — Synthesises all agent outputs into a structured compliance
report (HTML + JSON).

Input  (JSON): { "changes": [...], "mappings": [...], "drafts": [...],
                 "doc_metadata": {...} }
Output (JSON): { "report_html": str, "report_json": dict, "report_path": str }
─────────────────────────────────────────────────────────────────────────────
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.llm_client import get_llm_client, build_prompt

REPORTS_DIR = os.getenv("REPORTS_DIR", "./data/reports")

# ── Executive Summary Prompt ──────────────────────────────────────────────────

SUMMARY_PROMPT = """\
You are the Chief Compliance Officer of an Indian financial institution.

A regulatory document has been analysed. Here are the key findings:

Total changes   : {total_changes}
High-risk items : {high_count}
Medium-risk items: {medium_count}
Low-risk items  : {low_count}
Policies affected: {policy_count}

Top changes:
{top_changes}

Write a 3–5 sentence executive summary for senior management. Be direct,
professional, and highlight the most urgent actions needed.
"""


def _build_executive_summary(changes, mappings, drafts, llm) -> str:
    high   = sum(1 for c in changes if c.get("risk") == "HIGH")
    medium = sum(1 for c in changes if c.get("risk") == "MEDIUM")
    low    = sum(1 for c in changes if c.get("risk") == "LOW")

    policy_ids = set()
    for m in mappings:
        for p in m.get("matched_policies", []):
            policy_ids.add(p["policy_id"])

    top_changes = "\n".join(
        f"- [{c.get('risk')}] {c.get('summary', '')[:120]}"
        for c in changes[:5]
    )

    prompt = build_prompt(SUMMARY_PROMPT, {
        "total_changes": len(changes),
        "high_count":    high,
        "medium_count":  medium,
        "low_count":     low,
        "policy_count":  len(policy_ids),
        "top_changes":   top_changes or "No changes.",
    })

    try:
        result = llm.invoke(prompt)
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        return f"Executive summary unavailable ({e}). Manual review required."


# ── HTML Report Template ──────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Compliance Report – {doc_name}</title>
<style>
  :root {{
    --bg: #0f1117; --surface: #1a1d27; --card: #22263a;
    --accent: #7c6af7; --accent2: #06b6d4; --text: #e2e8f0;
    --muted: #94a3b8; --border: #2d3248;
    --high: #ef4444; --medium: #f59e0b; --low: #22c55e;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg);
          color: var(--text); line-height: 1.6; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 2rem; }}

  /* Header */
  .report-header {{ text-align: center; padding: 2.5rem 0 2rem;
    border-bottom: 1px solid var(--border); margin-bottom: 2rem; }}
  .report-header h1 {{ font-size: 2rem; font-weight: 700;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }}
  .report-header .meta {{ color: var(--muted); margin-top: .5rem; font-size: .9rem; }}

  /* Summary cards */
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr));
    gap: 1rem; margin-bottom: 2rem; }}
  .stat-card {{ background: var(--card); border-radius: 12px; padding: 1.25rem;
    text-align: center; border: 1px solid var(--border); }}
  .stat-card .num {{ font-size: 2rem; font-weight: 800; }}
  .stat-card .lbl {{ color: var(--muted); font-size: .8rem; margin-top: .25rem; }}
  .stat-card.high  .num {{ color: var(--high); }}
  .stat-card.medium .num {{ color: var(--medium); }}
  .stat-card.low   .num {{ color: var(--low); }}
  .stat-card.total .num {{ color: var(--accent); }}

  /* Section */
  .section {{ margin-bottom: 2.5rem; }}
  .section h2 {{ font-size: 1.2rem; font-weight: 600; color: var(--accent2);
    border-left: 4px solid var(--accent); padding-left: .75rem;
    margin-bottom: 1.25rem; }}

  /* Executive summary */
  .exec-summary {{ background: var(--card); border-radius: 12px; padding: 1.5rem;
    border: 1px solid var(--border); color: var(--text); line-height: 1.8; }}

  /* Change / Draft cards */
  .card {{ background: var(--card); border-radius: 12px; padding: 1.25rem;
    margin-bottom: 1rem; border: 1px solid var(--border);
    border-left: 4px solid var(--border); }}
  .card.HIGH   {{ border-left-color: var(--high); }}
  .card.MEDIUM {{ border-left-color: var(--medium); }}
  .card.LOW    {{ border-left-color: var(--low); }}
  .card.NEW    {{ border-left-color: var(--accent); }}

  .badge {{ display: inline-block; padding: .2rem .65rem; border-radius: 9999px;
    font-size: .72rem; font-weight: 700; letter-spacing: .05em; }}
  .badge.HIGH   {{ background: rgba(239,68,68,.15); color: var(--high); }}
  .badge.MEDIUM {{ background: rgba(245,158,11,.15); color: var(--medium); }}
  .badge.LOW    {{ background: rgba(34,197,94,.15); color: var(--low); }}
  .badge.ADDED  {{ background: rgba(34,197,94,.15); color: var(--low); }}
  .badge.REMOVED{{ background: rgba(239,68,68,.15); color: var(--high); }}
  .badge.MODIFIED{{ background: rgba(124,106,247,.15); color: var(--accent); }}
  .badge.NEW    {{ background: rgba(6,182,212,.15); color: var(--accent2); }}

  .card-title {{ font-weight: 600; margin-bottom: .5rem; }}
  .card-meta  {{ color: var(--muted); font-size: .82rem; margin-bottom: .75rem; }}
  .snippet    {{ background: var(--surface); border-radius: 8px; padding: .75rem;
    font-size: .85rem; color: var(--muted); margin-top: .5rem;
    border: 1px solid var(--border); white-space: pre-wrap; word-break: break-word; }}
  .draft-text {{ background: rgba(124,106,247,.08); border-radius: 8px; 
    padding: .85rem; font-size: .88rem; border: 1px solid rgba(124,106,247,.25);
    white-space: pre-wrap; word-break: break-word; margin-top: .5rem; }}
  .rationale  {{ color: var(--accent2); font-size: .82rem; margin-top: .5rem; 
    font-style: italic; }}

  /* Risk Score Gauge */
  .risk-gauge {{ display: flex; align-items: center; gap: .5rem; margin: .5rem 0; }}
  .gauge-bar {{ flex: 1; height: 8px; background: var(--surface); border-radius: 4px; overflow: hidden; }}
  .gauge-fill {{ height: 100%; border-radius: 4px; transition: width .5s ease; }}
  .gauge-fill.HIGH   {{ background: linear-gradient(90deg, var(--high), #f87171); }}
  .gauge-fill.MEDIUM {{ background: linear-gradient(90deg, var(--medium), #fbbf24); }}
  .gauge-fill.LOW    {{ background: linear-gradient(90deg, var(--low), #4ade80); }}
  .gauge-val {{ font-size: .75rem; font-weight: 700; min-width: 40px; text-align: right; }}
  .breakdown-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: .5rem; margin-top: .5rem; }}
  .bd-item {{ background: var(--surface); padding: .5rem; border-radius: 8px; text-align: center; font-size: .72rem; }}
  .bd-item .bd-val {{ font-size: 1rem; font-weight: 700; }}

  /* Deadline */
  .deadline-card {{ background: var(--card); border-radius: 12px; padding: 1rem;
    margin-bottom: .75rem; border: 1px solid var(--border);
    display: flex; align-items: center; gap: 1rem; }}
  .dl-days {{ font-size: 1.5rem; font-weight: 800; min-width: 60px; text-align: center; }}
  .dl-days.CRITICAL {{ color: var(--high); }}
  .dl-days.URGENT   {{ color: var(--medium); }}
  .dl-days.NORMAL   {{ color: var(--low); }}
  .dl-info {{ flex: 1; }}
  .dl-desc {{ font-weight: 600; font-size: .85rem; }}
  .dl-meta {{ font-size: .75rem; color: var(--muted); }}

  /* Explanation */
  .explanation {{ background: rgba(6,182,212,.06); border: 1px solid rgba(6,182,212,.15);
    border-radius: 8px; padding: .6rem .8rem; font-size: .78rem; color: var(--accent2);
    margin-top: .4rem; font-style: italic; }}

  /* Footer */
  footer {{ text-align: center; color: var(--muted); font-size: .8rem;
    padding: 2rem 0; border-top: 1px solid var(--border); margin-top: 2rem; }}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="report-header">
    <h1>⚖️ Compliance Intelligence Report</h1>
    <div class="meta">
      Document: <strong>{doc_name}</strong> &nbsp;|&nbsp;
      Generated: <strong>{generated_at}</strong> &nbsp;|&nbsp;
      Pages: <strong>{page_count}</strong>
    </div>
  </div>

  <!-- Stats -->
  <div class="stats-grid">
    <div class="stat-card total">
      <div class="num">{total_changes}</div>
      <div class="lbl">Total Changes</div>
    </div>
    <div class="stat-card high">
      <div class="num">{high_count}</div>
      <div class="lbl">High Risk</div>
    </div>
    <div class="stat-card medium">
      <div class="num">{medium_count}</div>
      <div class="lbl">Medium Risk</div>
    </div>
    <div class="stat-card low">
      <div class="num">{low_count}</div>
      <div class="lbl">Low Risk</div>
    </div>
    <div class="stat-card total">
      <div class="num">{policy_count}</div>
      <div class="lbl">Policies Affected</div>
    </div>
    <div class="stat-card total">
      <div class="num">{draft_count}</div>
      <div class="lbl">Drafts Generated</div>
    </div>
  </div>

  <!-- Executive Summary -->
  <div class="section">
    <h2>Executive Summary</h2>
    <div class="exec-summary">{executive_summary}</div>
  </div>

  <!-- Detected Changes -->
  <div class="section">
    <h2>Detected Regulatory Changes</h2>
    {changes_html}
  </div>

  <!-- Affected Policies -->
  <div class="section">
    <h2>Affected Policies &amp; Analysis</h2>
    {mappings_html}
  </div>

  <!-- Suggested Updates -->
  <div class="section">
    <h2>Suggested Policy Updates (Drafts)</h2>
    {drafts_html}
  </div>

  <!-- Compliance Deadlines -->
  <div class="section">
    <h2>⏰ Compliance Deadlines</h2>
    {deadlines_html}
  </div>

</div>
<footer>
  Generated by Autonomous Compliance &amp; Regulatory Intelligence System &nbsp;|&nbsp;
  {generated_at}
</footer>
</body>
</html>"""


# ── HTML builders ─────────────────────────────────────────────────────────────

def _changes_html(changes: list[dict]) -> str:
    if not changes:
        return "<p style='color:var(--muted)'>No changes detected.</p>"
    parts = []
    for c in changes:
        risk = c.get("risk", "LOW")
        ctype = c.get("type", "MODIFIED")
        # Risk score gauge
    risk_score = c.get("risk_score", 0)
    gauge_html = ""
    if risk_score:
        gauge_html = f"""<div class="risk-gauge">
  <div class="gauge-bar"><div class="gauge-fill {risk}" style="width:{risk_score}%"></div></div>
  <div class="gauge-val" style="color:var(--{risk.lower()})">{risk_score}/100</div>
</div>"""
    # Breakdown
    bd = c.get("risk_breakdown", {})
    bd_html = ""
    if bd:
        bd_html = f"""<div class="breakdown-grid">
  <div class="bd-item"><div class="bd-val">{bd.get('compliance',0)}</div>Compliance</div>
  <div class="bd-item"><div class="bd-val">{bd.get('financial',0)}</div>Financial</div>
  <div class="bd-item"><div class="bd-val">{bd.get('operational',0)}</div>Operational</div>
  <div class="bd-item"><div class="bd-val">{bd.get('reputational',0)}</div>Reputational</div>
</div>"""
    reasoning = c.get("risk_reasoning", "")
    reason_html = f"<div class='explanation'>🔍 {reasoning[:300]}</div>" if reasoning else ""

    parts.append(f"""
<div class="card {risk}">
  <div class="card-title">
    <span class="badge {risk}">{risk}</span>&nbsp;
    <span class="badge {ctype}">{ctype}</span>&nbsp;
    {c.get("section", "General")}
  </div>
  <div class="card-meta">{c.get("summary", "")[:200]}</div>
  {gauge_html}
  {bd_html}
  {reason_html}
  {"<div class='snippet'><strong>Before:</strong> " + (c.get("old") or "N/A")[:300] + "</div>" if c.get("old") else ""}
  {"<div class='snippet' style='margin-top:.5rem'><strong>After:</strong> " + (c.get("new") or "N/A")[:300] + "</div>" if c.get("new") else ""}
</div>""")
    return "\n".join(parts)


def _mappings_html(mappings: list[dict]) -> str:
    if not mappings:
        return "<p style='color:var(--muted)'>No mappings generated.</p>"
    parts = []
    for m in mappings:
        change  = m.get("change", {})
        risk    = change.get("risk", "LOW")
        matched = m.get("matched_policies", [])
        analysis = m.get("llm_analysis", "")

        pol_lines = []
        for p in matched:
            conf = p.get('confidence_pct', round(p.get('score', 0) * 100, 1))
            expl = p.get('match_explanation', '')
            pol_lines.append(
                f"<span class='badge MODIFIED'>{p['policy_title']} ({conf}%)</span>"
            )
            if expl:
                pol_lines.append(f"<div class='explanation'>💡 {expl[:250]}</div>")
        pol_html = " ".join(pol_lines) if pol_lines else "<span class='badge LOW'>No policy matched</span>"

        parts.append(f"""
<div class="card {risk}">
  <div class="card-title">{change.get("section","General")} — {change.get("type","")}</div>
  <div class="card-meta">Matched policies: {pol_html}</div>
  <div class="snippet">{analysis[:600]}</div>
</div>""")
    return "\n".join(parts)


def _drafts_html(drafts: list[dict]) -> str:
    if not drafts:
        return "<p style='color:var(--muted)'>No drafts generated.</p>"
    parts = []
    for d in drafts:
        risk = d.get("risk", "LOW")
        pid  = d.get("policy_id", "NEW")
        parts.append(f"""
<div class="card {risk if pid != 'NEW' else 'NEW'}">
  <div class="card-title">
    <span class="badge {'NEW' if pid=='NEW' else risk}">{pid}</span>&nbsp;
    {d.get("policy_title","")}
  </div>
  <div class="card-meta">{d.get("change_summary","")[:200]}</div>
  <div class="draft-text">{d.get("draft_update","")}</div>
  <div class="rationale">📌 {d.get("rationale","")}</div>
</div>""")
    return "\n".join(parts)


def _deadlines_html(deadlines: list[dict]) -> str:
    if not deadlines:
        return "<p style='color:var(--muted)'>No deadlines extracted.</p>"
    parts = []
    for d in deadlines:
        urgency = d.get("urgency", "NORMAL")
        days = d.get("days", 0)
        day_label = "TODAY" if days == 0 else f"{days}d"
        parts.append(f"""
<div class="deadline-card">
  <div class="dl-days {urgency}">{day_label}</div>
  <div class="dl-info">
    <div class="dl-desc">{d.get("description", "")}</div>
    <div class="dl-meta">
      Section: {d.get("section", "General")} &nbsp;|&nbsp;
      Due: {d.get("due_date", "TBD")} &nbsp;|&nbsp;
      <span class="badge {d.get('risk','LOW')}">{d.get('risk','LOW')}</span>
    </div>
  </div>
</div>""")
    return "\n".join(parts)


# ── Public API ────────────────────────────────────────────────────────────────

def run(state: dict[str, Any]) -> dict[str, Any]:
    """
    Report Agent entry-point.

    State keys consumed
    -------------------
    changes      : list[dict]
    mappings     : list[dict]
    drafts       : list[dict]
    doc_metadata : dict
    """
    changes      = state.get("changes", [])
    mappings     = state.get("mappings", [])
    drafts       = state.get("drafts", [])
    doc_meta     = state.get("doc_metadata", {})

    llm = get_llm_client()
    exec_summary = _build_executive_summary(changes, mappings, drafts, llm)

    high   = sum(1 for c in changes if c.get("risk") == "HIGH")
    medium = sum(1 for c in changes if c.get("risk") == "MEDIUM")
    low    = sum(1 for c in changes if c.get("risk") == "LOW")

    policy_ids = set()
    for m in mappings:
        for p in m.get("matched_policies", []):
            policy_ids.add(p["policy_id"])

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    doc_name = doc_meta.get("file_name", "Unknown")

    report_html = HTML_TEMPLATE.format(
        doc_name        = doc_name,
        generated_at    = generated_at,
        page_count      = doc_meta.get("page_count", "N/A"),
        total_changes   = len(changes),
        high_count      = high,
        medium_count    = medium,
        low_count       = low,
        policy_count    = len(policy_ids),
        draft_count     = len(drafts),
        executive_summary = exec_summary.replace("\n", "<br>"),
        changes_html    = _changes_html(changes),
        mappings_html   = _mappings_html(mappings),
        drafts_html     = _drafts_html(drafts),
        deadlines_html  = _deadlines_html(state.get("all_deadlines", [])),
    )

    # Persist report
    Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORTS_DIR, f"report_{ts}.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_html)

    # Structured JSON summary
    report_json = {
        "generated_at":      generated_at,
        "document":          doc_name,
        "executive_summary": exec_summary,
        "stats": {
            "total_changes": len(changes),
            "high":          high,
            "medium":        medium,
            "low":           low,
            "policies_affected": len(policy_ids),
            "drafts_generated":  len(drafts),
        },
        "all_deadlines": state.get("all_deadlines", []),
        "changes":  changes,
        "mappings": [
            {
                "section":          m["change"].get("section"),
                "matched_policies": m["matched_policies"],
                "analysis":         m["llm_analysis"],
            }
            for m in mappings
        ],
        "drafts": drafts,
    }

    json_path = report_path.replace(".html", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2, ensure_ascii=False)

    print(f"[ReportAgent] ✅  Report saved → {report_path}")
    return {**state, "report_html": report_html, "report_json": report_json,
            "report_path": report_path}
