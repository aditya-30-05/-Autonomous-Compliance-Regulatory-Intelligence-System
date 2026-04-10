/**
 * app.js — ComplianceAI v2.0 Frontend
 * ─────────────────────────────────────────────────
 * 8-agent pipeline, risk gauges, deadlines, explain-in-simple-terms,
 * confidence bars, monitoring simulation, word-level diff.
 */

const API = window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost"
  ? "http://localhost:8000"
  : "";

let sessionId  = null;
let newFile    = null;
let oldFile    = null;
let currentData = null;

/* ═══════════════════════════ INIT ═════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  initNotificationBanner();
  initNavbar();
  initFileInputs();
  initParticles();
  loadHistory();
  startMonitoringFeed();
});

/* ═══════════════════════════ HEALTH CHECK ═════════════════════════════════ */

async function checkHealth() {
  const ind = document.getElementById("api-indicator");
  try {
    const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(3000) });
    if (r.ok) {
      const d = await r.json();
      ind.classList.add("online");
      ind.querySelector(".api-label").textContent = `Online · v${d.version || "1.0"}`;
    }
  } catch {
    ind.classList.add("offline");
    ind.querySelector(".api-label").textContent = "Offline";
  }
}

/* ═══════════════════════════ NOTIFICATION ═════════════════════════════════ */

function initNotificationBanner() {
  const close = document.getElementById("notif-close");
  if (close) close.addEventListener("click", () => {
    document.getElementById("notif-banner").style.display = "none";
  });
}

/* ═══════════════════════════ NAVBAR ═══════════════════════════════════════ */

function initNavbar() {
  const nav = document.getElementById("navbar");
  window.addEventListener("scroll", () => {
    nav.classList.toggle("scrolled", window.scrollY > 50);
  });

  // Mobile menu
  const btn = document.getElementById("mobile-menu-btn");
  const menu = document.getElementById("mobile-menu");
  if (btn && menu) {
    btn.addEventListener("click", () => {
      btn.classList.toggle("active");
      menu.classList.toggle("open");
    });
    menu.querySelectorAll("a").forEach(a => {
      a.addEventListener("click", () => {
        btn.classList.remove("active");
        menu.classList.remove("open");
      });
    });
  }
}

/* ═══════════════════════════ PARTICLES ════════════════════════════════════ */

function initParticles() {
  const wrap = document.getElementById("hero-particles");
  if (!wrap) return;
  for (let i = 0; i < 30; i++) {
    const p = document.createElement("div");
    p.className = "particle";
    p.style.cssText = `left:${Math.random()*100}%;top:${Math.random()*100}%;width:${2+Math.random()*3}px;height:${2+Math.random()*3}px;animation-delay:${Math.random()*6}s;animation-duration:${4+Math.random()*8}s`;
    wrap.appendChild(p);
  }
}

/* ═══════════════════════════ FILE UPLOAD ══════════════════════════════════ */

function initFileInputs() {
  document.getElementById("input-new")?.addEventListener("change", e => {
    if (e.target.files[0]) setFile("new", e.target.files[0]);
  });
  document.getElementById("input-old")?.addEventListener("change", e => {
    if (e.target.files[0]) setFile("old", e.target.files[0]);
  });
}

function setFile(type, file) {
  if (type === "new") newFile = file; else oldFile = file;
  const badge = document.getElementById(`file-${type}`);
  const card = document.getElementById(`drop-${type}`);
  badge.textContent = file.name;
  card.classList.add("has-file");
}

function dragOver(e, type) {
  e.preventDefault();
  document.getElementById(`drop-${type}`).classList.add("dragover");
}
function dragLeave(e, type) {
  document.getElementById(`drop-${type}`).classList.remove("dragover");
}
function dropFile(e, type) {
  e.preventDefault();
  document.getElementById(`drop-${type}`).classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) setFile(type, file);
}

async function uploadFiles() {
  if (!newFile) return showMsg("msg-upload", "Please select the new circular PDF.", "error");
  const btn = document.getElementById("btn-upload");
  const txt = document.getElementById("btn-upload-text");
  btn.disabled = true;
  txt.textContent = "Uploading…";

  const fd = new FormData();
  fd.append("new_pdf", newFile);
  if (oldFile) fd.append("old_pdf", oldFile);

  try {
    const r = await fetch(`${API}/upload`, { method: "POST", body: fd });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Upload failed");
    sessionId = d.session_id;
    document.getElementById("session-display").textContent = sessionId.slice(0, 12) + "…";
    document.getElementById("session-row").style.display = "flex";
    document.getElementById("btn-run").disabled = false;
    showMsg("msg-upload", `✓ Uploaded successfully. Session: ${sessionId.slice(0, 12)}`, "success");
  } catch (err) {
    showMsg("msg-upload", `✗ ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    txt.textContent = "Upload Documents";
  }
}

/* ═══════════════════════════ RUN PIPELINE ═════════════════════════════════ */

const AGENTS = ["parser", "diff", "risk_scorer", "mapper", "explainer", "drafter", "deadline", "reporter"];

async function runPipeline() {
  if (!sessionId) return showMsg("msg-run", "Upload files first.", "error");

  const btn = document.getElementById("btn-run");
  const txt = document.getElementById("btn-run-text");
  btn.disabled = true;
  txt.textContent = "Running…";

  const log = document.getElementById("agent-log");
  log.style.display = "flex";

  // Reset log
  AGENTS.forEach(a => {
    const el = document.getElementById(`log-${a}`);
    if (el) {
      el.classList.remove("done", "active");
      el.querySelector(".log-icon").textContent = "⏳";
    }
  });

  // Animate agents
  animatePipeline();

  const fd = new FormData();
  fd.append("session_id", sessionId);

  try {
    const r = await fetch(`${API}/run`, { method: "POST", body: fd });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Pipeline failed");

    // Complete all agents
    AGENTS.forEach(a => markAgent(a, "done"));
    document.getElementById("pipeline-line-fill").style.width = "100%";

    showMsg("msg-run", "✓ Pipeline complete — 8 agents finished.", "success");
    fetchAndRenderResults();
  } catch (err) {
    showMsg("msg-run", `✗ ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    txt.textContent = "Run AI Analysis";
  }
}

function animatePipeline() {
  const fill = document.getElementById("pipeline-line-fill");
  AGENTS.forEach((a, i) => {
    setTimeout(() => {
      markAgent(a, "active");
      fill.style.width = `${((i + 0.5) / AGENTS.length) * 100}%`;
      if (i > 0) markAgent(AGENTS[i - 1], "done");
    }, i * 1500);
  });
}

function markAgent(name, state) {
  const node = document.getElementById(`pnode-${name}`);
  const logItem = document.getElementById(`log-${name}`);
  if (node) {
    node.classList.remove("active", "done");
    node.classList.add(state);
  }
  if (logItem) {
    logItem.classList.remove("active", "done");
    logItem.classList.add(state);
    const icon = logItem.querySelector(".log-icon");
    if (state === "active") icon.textContent = "⟳";
    if (state === "done") icon.textContent = "✓";
  }
}

/* ═══════════════════════════ FETCH RESULTS ════════════════════════════════ */

async function fetchAndRenderResults() {
  try {
    const r = await fetch(`${API}/report/json`);
    const d = await r.json();
    renderResults(d);
  } catch {
    showMsg("msg-run", "Could not fetch results. Use Load Demo Data instead.", "info");
  }
}

/* ═══════════════════════════ RENDER RESULTS ═══════════════════════════════ */

function renderResults(data) {
  currentData = data;
  document.getElementById("output-section").style.display = "block";
  document.getElementById("report-section").style.display = "block";

  renderStats(data);
  renderChanges(data.changes || []);
  renderPolicies(data.mappings || []);
  renderDrafts(data.drafts || []);
  renderDeadlines(data.all_deadlines || []);
  renderTimeline(data.changes || []);
  updateHistory(data);

  document.getElementById("output-section").scrollIntoView({ behavior: "smooth" });
}

/* ─── Stats Row ─── */
function renderStats(data) {
  const s = data.stats || {};
  const dl = (data.all_deadlines || []).length;
  const html = `
    <div class="stat-card"><div class="stat-top high"></div><div class="stat-num gradient-red">${s.total_changes||0}</div><div class="stat-label">Changes</div></div>
    <div class="stat-card"><div class="stat-top" style="background:var(--red)"></div><div class="stat-num gradient-red">${s.high||0}</div><div class="stat-label">High Risk</div></div>
    <div class="stat-card"><div class="stat-top" style="background:var(--amber)"></div><div class="stat-num gradient-amber">${s.medium||0}</div><div class="stat-label">Medium Risk</div></div>
    <div class="stat-card"><div class="stat-top" style="background:var(--green)"></div><div class="stat-num gradient-green">${s.low||0}</div><div class="stat-label">Low Risk</div></div>
    <div class="stat-card"><div class="stat-top" style="background:var(--cyan)"></div><div class="stat-num gradient-cyan">${s.policies_affected||0}</div><div class="stat-label">Policies</div></div>
    <div class="stat-card"><div class="stat-top" style="background:var(--accent)"></div><div class="stat-num gradient-accent">${s.drafts_generated||0}</div><div class="stat-label">Drafts</div></div>
    <div class="stat-card"><div class="stat-top" style="background:var(--amber)"></div><div class="stat-num gradient-amber">${dl}</div><div class="stat-label">Deadlines</div></div>
  `;
  document.getElementById("stats-row").innerHTML = html;
}

/* ─── Changes Tab (with risk gauge, word diff, explain button) ─── */
function renderChanges(changes) {
  const panel = document.getElementById("tab-changes");
  if (!changes.length) { panel.innerHTML = "<p class='empty'>No changes detected.</p>"; return; }

  panel.innerHTML = changes.map((c, i) => {
    const risk = c.risk || "LOW";
    const score = c.risk_score || 0;
    const bd = c.risk_breakdown || {};

    // Word-level diff
    const diffHtml = generateWordDiff(c.old || "", c.new || "");

    // Risk gauge
    const gaugeHtml = score ? `
      <div class="risk-gauge">
        <div class="gauge-bar"><div class="gauge-fill ${risk}" style="width:${score}%"></div></div>
        <div class="gauge-val ${risk}">${score}/100</div>
      </div>` : "";

    // Breakdown
    const bdHtml = Object.keys(bd).length ? `
      <div class="breakdown-grid">
        <div class="bd-item"><div class="bd-val">${bd.compliance||0}</div><div class="bd-label">Compliance</div></div>
        <div class="bd-item"><div class="bd-val">${bd.financial||0}</div><div class="bd-label">Financial</div></div>
        <div class="bd-item"><div class="bd-val">${bd.operational||0}</div><div class="bd-label">Operational</div></div>
        <div class="bd-item"><div class="bd-val">${bd.reputational||0}</div><div class="bd-label">Reputational</div></div>
      </div>` : "";

    // Reasoning
    const reasonHtml = c.risk_reasoning
      ? `<div class="risk-reasoning">${c.risk_reasoning}</div>` : "";

    // Deadline pills
    const dlHtml = (c.deadlines || []).map(d => `
      <span class="badge ${d.urgency === 'CRITICAL' ? 'HIGH' : d.urgency === 'URGENT' ? 'MEDIUM' : 'LOW'}">
        ⏰ ${d.days}d — ${d.description}
      </span>`).join("");

    return `
      <div class="change-card" style="animation-delay:${i * .08}s">
        <div class="change-header">
          <div>
            <span class="badge ${risk}">${risk}</span>
            <span class="badge ${c.type || 'MODIFIED'}">${c.type || 'MODIFIED'}</span>
            <strong>${c.section || 'General'}</strong>
          </div>
        </div>
        <div class="change-summary">${c.summary || ''}</div>
        ${gaugeHtml}
        ${bdHtml}
        ${reasonHtml}
        <div class="diff-block">
          <div class="diff-side diff-old">
            <div class="diff-label">− OLD</div>
            <div class="diff-text">${c.old || '<span style="opacity:.4">N/A</span>'}</div>
          </div>
          <div class="diff-side diff-new">
            <div class="diff-label">+ NEW</div>
            <div class="diff-text">${c.new || '<span style="opacity:.4">N/A</span>'}</div>
          </div>
        </div>
        ${diffHtml ? `<div style="margin-top:.5rem"><strong style="font-size:.72rem;color:var(--text-3)">WORD DIFF:</strong><div class="word-diff">${diffHtml}</div></div>` : ''}
        ${dlHtml ? `<div style="margin-top:.5rem;display:flex;flex-wrap:wrap;gap:.3rem">${dlHtml}</div>` : ''}
        <button class="btn-explain" onclick="explainChange(${i})">
          💡 Explain in Simple Terms
        </button>
        <div class="explain-result" id="explain-${i}"></div>
      </div>`;
  }).join("");
}

/* ─── Word-level diff ─── */
function generateWordDiff(oldText, newText) {
  if (!oldText || !newText) return "";
  const oldWords = oldText.split(/\s+/);
  const newWords = newText.split(/\s+/);

  // Simple LCS-based diff
  const result = [];
  let oi = 0, ni = 0;
  const maxLen = Math.max(oldWords.length, newWords.length);
  if (maxLen > 80) return ""; // Skip very long texts

  while (oi < oldWords.length || ni < newWords.length) {
    if (oi < oldWords.length && ni < newWords.length && oldWords[oi] === newWords[ni]) {
      result.push(oldWords[oi]);
      oi++; ni++;
    } else if (ni < newWords.length && (oi >= oldWords.length || !oldWords.slice(oi).includes(newWords[ni]))) {
      result.push(`<span class="word-ins">${newWords[ni]}</span>`);
      ni++;
    } else {
      result.push(`<span class="word-del">${oldWords[oi]}</span>`);
      oi++;
    }
  }
  return result.join(" ");
}

/* ─── Explain in Simple Terms ─── */
async function explainChange(index) {
  const el = document.getElementById(`explain-${index}`);
  if (el.classList.contains("visible")) { el.classList.remove("visible"); return; }

  const change = currentData?.changes?.[index];
  if (!change) return;

  el.textContent = "Generating simple explanation…";
  el.classList.add("visible");

  try {
    const r = await fetch(`${API}/summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(change),
    });
    const d = await r.json();
    el.textContent = d.summary || "Summary unavailable.";
  } catch {
    // Fallback: generate locally
    el.textContent = generateLocalSummary(change);
  }
}

function generateLocalSummary(change) {
  const section = change.section || "this area";
  const risk = (change.risk || "LOW").toLowerCase();
  const type = (change.type || "modified").toLowerCase();
  const summaries = {
    HIGH: `⚠️ This is a critical change in ${section}. The regulator has ${type} requirements that could result in penalties or enforcement action if not addressed promptly. Your compliance team should prioritize reviewing and updating existing procedures.`,
    MEDIUM: `📋 This is a moderate change in ${section}. The regulator has ${type} certain guidelines that may require adjustments to your internal policies. Review is recommended within the next compliance cycle.`,
    LOW: `ℹ️ This is a minor update in ${section}. The ${type} change has limited immediate impact but should be noted for future reference and gradual policy alignment.`,
  };
  return summaries[change.risk || "LOW"] || summaries.LOW;
}

/* ─── Policies Tab (with confidence score + explanation) ─── */
function renderPolicies(mappings) {
  const panel = document.getElementById("tab-policies");
  if (!mappings.length) { panel.innerHTML = "<p class='empty'>No policy mappings available.</p>"; return; }

  panel.innerHTML = mappings.map((m, i) => {
    const change = m.change || {};
    const policies = m.matched_policies || [];
    const analysis = m.llm_analysis || "";

    const policyCards = policies.map(p => {
      const conf = p.confidence_pct || Math.round((p.score || 0) * 100);
      const explain = p.match_explanation || "";
      return `
        <div style="padding:.5rem 0;border-bottom:1px solid var(--border-dim)">
          <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap">
            <span class="badge MODIFIED">${p.policy_title}</span>
            <span class="badge LOW">${p.policy_id}</span>
          </div>
          <div class="confidence-bar">
            <div class="conf-track"><div class="conf-fill" style="width:${conf}%"></div></div>
            <div class="conf-pct">${conf}%</div>
            <span style="font-size:.68rem;color:var(--text-3)">confidence</span>
          </div>
          ${explain ? `<div class="match-explain">${explain}</div>` : ''}
        </div>`;
    }).join("");

    return `
      <div class="change-card" style="animation-delay:${i * .08}s">
        <div class="change-header">
          <span class="badge ${change.risk||'LOW'}">${change.risk||'LOW'}</span>
          <strong>${change.section || 'General'}</strong>
        </div>
        <div class="change-summary">${change.summary || ''}</div>
        ${policyCards || '<p style="color:var(--text-3);font-size:.82rem">No policies matched</p>'}
        ${analysis ? `<div style="margin-top:.5rem;padding:.6rem .8rem;background:var(--bg-surface);border-radius:8px;font-size:.8rem;color:var(--text-2)">${analysis.slice(0, 500)}</div>` : ''}
      </div>`;
  }).join("");
}

/* ─── Drafts Tab ─── */
function renderDrafts(drafts) {
  const panel = document.getElementById("tab-drafts");
  if (!drafts.length) { panel.innerHTML = "<p class='empty'>No drafts generated.</p>"; return; }

  panel.innerHTML = drafts.map((d, i) => `
    <div class="change-card" style="animation-delay:${i * .08}s">
      <div class="change-header">
        <span class="badge ${d.risk||'LOW'}">${d.risk||'LOW'}</span>
        <strong>${d.policy_title || 'New Policy'}</strong>
        <span class="badge MODIFIED">${d.policy_id || 'NEW'}</span>
      </div>
      <div class="change-summary">${d.change_summary || ''}</div>
      <div style="margin-top:.5rem;padding:.8rem;background:var(--bg-surface);border:1px solid var(--border-dim);border-radius:8px;font-size:.82rem;line-height:1.6;color:var(--text-1);white-space:pre-wrap">${d.draft_update || 'No draft content'}</div>
      <div style="margin-top:.5rem;font-size:.78rem;color:var(--cyan);font-style:italic">📎 ${d.rationale || 'No rationale provided'}</div>
    </div>
  `).join("");
}

/* ─── Deadlines Tab ─── */
function renderDeadlines(deadlines) {
  const panel = document.getElementById("tab-deadlines");
  if (!deadlines.length) {
    panel.innerHTML = "<p class='empty'>No compliance deadlines extracted.</p>";
    return;
  }

  panel.innerHTML = `<div class="deadline-grid">${deadlines.map(d => {
    const urg = d.urgency || "NORMAL";
    const dayLabel = d.days === 0 ? "NOW" : d.days;
    const unitLabel = d.days === 0 ? "IMMEDIATE" : "DAYS";
    return `
      <div class="deadline-card ${urg}">
        <div class="dl-countdown ${urg}">
          <div class="dl-days ${urg}">${dayLabel}</div>
          <div class="dl-unit">${unitLabel}</div>
        </div>
        <div class="dl-info">
          <div class="dl-desc">${d.description || ''}</div>
          <div class="dl-meta">
            <span class="badge ${d.risk||'LOW'}">${d.risk||'LOW'}</span>
            <span>${d.section || 'General'}</span>
            <span>Due: ${d.due_date || 'TBD'}</span>
          </div>
        </div>
      </div>`;
  }).join("")}</div>`;
}

/* ─── Timeline Tab ─── */
function renderTimeline(changes) {
  const panel = document.getElementById("tab-timeline");
  if (!changes.length) { panel.innerHTML = "<p class='empty'>No timeline data.</p>"; return; }

  panel.innerHTML = `<div class="timeline">${changes.map((c, i) => `
    <div class="timeline-item" style="animation-delay:${i * .1}s">
      <div class="timeline-dot ${c.risk || 'LOW'}"></div>
      <div class="timeline-content">
        <div class="timeline-header">
          <span class="badge ${c.risk || 'LOW'}">${c.risk || 'LOW'}</span>
          ${c.risk_score ? `<span style="font-size:.72rem;color:var(--text-3);font-family:'JetBrains Mono',mono">Score: ${c.risk_score}/100</span>` : ''}
        </div>
        <div class="timeline-title">${c.section || 'General'}</div>
        <div class="timeline-desc">${c.summary || ''}</div>
        ${(c.deadlines||[]).length ? `<div style="margin-top:.3rem;font-size:.72rem;color:var(--amber)">⏰ ${c.deadlines.map(d=>d.description).join(', ')}</div>` : ''}
      </div>
    </div>
  `).join("")}</div>`;
}

/* ═══════════════════════════ MONITORING SIMULATION ════════════════════════ */

const MONITOR_EVENTS = [
  { time: "10:42", text: "RBI/2025-26/117 — Basel III Capital Adequacy (Revised)", badge: "HIGH", status: "live" },
  { time: "09:18", text: "SEBI/HO/MRD/2025/038 — Margin Requirements for F&O", badge: "MEDIUM", status: "live" },
  { time: "08:55", text: "RBI/2025-26/115 — IRRBB Framework Update", badge: "MEDIUM", status: "live" },
  { time: "07:30", text: "SEBI/HO/OIAE/2025/012 — Investor Grievance Redressal", badge: "LOW", status: "pending" },
  { time: "06:15", text: "RBI/2025-26/113 — Digital Lending Guidelines (Amendment)", badge: "HIGH", status: "pending" },
  { time: "Yesterday", text: "SEBI/HO/CFD/2025/007 — ESG Disclosure Framework", badge: "MEDIUM", status: "pending" },
];

function startMonitoringFeed() {
  const feed = document.getElementById("monitor-feed");
  if (!feed) return;

  MONITOR_EVENTS.forEach((ev, i) => {
    setTimeout(() => {
      const div = document.createElement("div");
      div.className = "monitor-item";
      div.innerHTML = `
        <div class="monitor-dot ${ev.status}"></div>
        <div class="monitor-time">${ev.time}</div>
        <div class="monitor-text">${ev.text}</div>
        <span class="monitor-badge badge ${ev.badge}">${ev.badge}</span>
      `;
      feed.appendChild(div);
    }, i * 400);
  });
}

/* ═══════════════════════════ REPORT ═══════════════════════════════════════ */

function viewReport() {
  const wrap = document.getElementById("report-frame-wrap");
  const frame = document.getElementById("report-frame");
  wrap.style.display = "block";
  frame.src = `${API}/report`;
}

function downloadReport() {
  window.open(`${API}/report/download`, "_blank");
}

/* ═══════════════════════════ TAB SWITCHING ════════════════════════════════ */

function switchTab(btn) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById(btn.dataset.tab).classList.add("active");
}

/* ═══════════════════════════ MESSAGES ═════════════════════════════════════ */

function showMsg(id, text, type) {
  const el = document.getElementById(id);
  el.className = `msg ${type}`;
  el.textContent = text;
  setTimeout(() => { el.className = "msg"; }, 8000);
}

/* ═══════════════════════════ HISTORY ══════════════════════════════════════ */

function loadHistory() {
  const tbody = document.getElementById("history-body");
  const history = [
    { doc: "RBI/2024-25/085 — KYC Master Direction", date: "2024-11-15", changes: 8, risk: "HIGH", deadlines: 3, status: "done" },
    { doc: "SEBI/HO/MRD/2024/052 — Trading Settlement", date: "2024-10-22", changes: 5, risk: "MEDIUM", deadlines: 1, status: "done" },
    { doc: "RBI/2024-25/071 — Digital Lending Update", date: "2024-09-18", changes: 12, risk: "HIGH", deadlines: 4, status: "done" },
    { doc: "SEBI/HO/CFD/2024/031 — LODR Amendment", date: "2024-08-05", changes: 3, risk: "LOW", deadlines: 0, status: "done" },
  ];

  tbody.innerHTML = history.map(h => `
    <tr>
      <td>${h.doc}</td>
      <td>${h.date}</td>
      <td>${h.changes}</td>
      <td><span class="badge ${h.risk}">${h.risk}</span></td>
      <td>${h.deadlines}</td>
      <td><span class="status-badge ${h.status}">${h.status}</span></td>
    </tr>
  `).join("");
}

function updateHistory(data) {
  const tbody = document.getElementById("history-body");
  const row = document.createElement("tr");
  const s = data.stats || {};
  const dl = (data.all_deadlines || []).length;
  row.innerHTML = `
    <td>${data.document || 'Latest Analysis'}</td>
    <td>${new Date().toISOString().slice(0, 10)}</td>
    <td>${s.total_changes || 0}</td>
    <td><span class="badge ${s.high > 0 ? 'HIGH' : s.medium > 0 ? 'MEDIUM' : 'LOW'}">${s.high > 0 ? 'HIGH' : s.medium > 0 ? 'MEDIUM' : 'LOW'}</span></td>
    <td>${dl}</td>
    <td><span class="status-badge done">done</span></td>
  `;
  tbody.insertBefore(row, tbody.firstChild);
}

/* ═══════════════════════════ DEMO DATA ════════════════════════════════════ */

function loadDemoData() {
  const demo = {
    generated_at: new Date().toISOString(),
    document: "RBI/2025-26/117 — Basel III Capital Adequacy (Revised April 2025)",
    executive_summary: "This circular introduces significant changes to capital adequacy requirements under Basel III norms. Key modifications include updated CAR thresholds, revised risk weights for certain asset classes, enhanced IRRBB framework, and new cybersecurity reporting requirements.",
    stats: {
      total_changes: 7,
      high: 2,
      medium: 3,
      low: 2,
      policies_affected: 5,
      drafts_generated: 6,
    },
    all_deadlines: [
      { text: "within 30 days", days: 30, due_date: "2025-05-10", urgency: "URGENT", description: "Capital adequacy ratio update required within 30 days", section: "Capital Adequacy", risk: "HIGH" },
      { text: "immediately", days: 0, due_date: new Date().toISOString().slice(0,10), urgency: "CRITICAL", description: "Cybersecurity incident reporting — immediate effect", section: "Cybersecurity", risk: "HIGH" },
      { text: "by June 30, 2025", days: 82, due_date: "2025-06-30", urgency: "NORMAL", description: "IRRBB framework implementation deadline", section: "IRRBB", risk: "MEDIUM" },
      { text: "within 90 days", days: 90, due_date: "2025-07-09", urgency: "NORMAL", description: "Updated disclosure formats due within 90 days", section: "Reporting", risk: "MEDIUM" },
    ],
    changes: [
      {
        type: "MODIFIED", section: "Capital Adequacy Ratio",
        old: "Banks shall maintain a minimum Capital Adequacy Ratio (CAR) of 9% with CET1 at 5.5% of risk-weighted assets on an ongoing basis.",
        new: "Banks shall maintain a minimum Capital Adequacy Ratio (CAR) of 11.5% with CET1 at 8% of risk-weighted assets. D-SIBs must maintain an additional buffer of 0.6%.",
        risk: "HIGH", risk_score: 82,
        risk_breakdown: { compliance: 85, financial: 90, operational: 60, reputational: 75 },
        risk_reasoning: "This change directly increases the minimum capital threshold by 250 basis points, impacting balance sheet planning, dividend distribution capacity, and potentially requiring additional capital raising for banks near the current threshold. Non-compliance carries strict enforcement action.",
        summary: "CAR increased from 9% to 11.5%, CET1 from 5.5% to 8%. D-SIB buffer of 0.6% added.",
        deadlines: [{ text: "within 30 days", days: 30, urgency: "URGENT", description: "Capital adequacy ratio update required within 30 days" }],
      },
      {
        type: "ADDED", section: "Cybersecurity Incident Reporting",
        old: null,
        new: "All regulated entities shall report cybersecurity incidents to RBI within 6 hours of detection. A dedicated CISO must be appointed with board-level reporting. Quarterly vulnerability assessments are mandatory.",
        risk: "HIGH", risk_score: 78,
        risk_breakdown: { compliance: 80, financial: 50, operational: 95, reputational: 85 },
        risk_reasoning: "New mandatory cybersecurity reporting within 6 hours creates significant operational burden. Failure to comply can result in penalties and reputational damage. Requires immediate CISO appointment and infrastructure changes.",
        summary: "New mandatory cybersecurity incident reporting to RBI within 6 hours. Requires CISO appointment.",
        deadlines: [{ text: "immediately", days: 0, urgency: "CRITICAL", description: "Cybersecurity incident reporting — immediate effect" }],
      },
      {
        type: "MODIFIED", section: "Interest Rate Risk in Banking Book (IRRBB)",
        old: "Banks shall measure interest rate risk using gap analysis on a quarterly basis.",
        new: "Banks shall implement a comprehensive IRRBB framework using EVE and NII sensitivity analysis, with monthly stress testing under at least six prescribed scenarios.",
        risk: "MEDIUM", risk_score: 58,
        risk_breakdown: { compliance: 65, financial: 70, operational: 55, reputational: 25 },
        risk_reasoning: "Transition from simple gap analysis to comprehensive EVE/NII framework requires significant system upgrades and staff retraining. Monthly stress testing increases operational frequency substantially.",
        summary: "IRRBB measurement upgraded from gap analysis to EVE/NII framework with monthly stress testing.",
        deadlines: [{ text: "by June 30, 2025", days: 82, urgency: "NORMAL", description: "IRRBB framework implementation deadline" }],
      },
      {
        type: "MODIFIED", section: "Risk Weight for Housing Loans",
        old: "Housing loans up to Rs 30 lakh shall carry a risk weight of 35%.",
        new: "Housing loans up to Rs 50 lakh shall carry a risk weight of 30%, with LTV-based tiering for amounts exceeding Rs 50 lakh.",
        risk: "MEDIUM", risk_score: 45,
        risk_breakdown: { compliance: 50, financial: 65, operational: 30, reputational: 15 },
        risk_reasoning: "Lower risk weights free up capital for housing lending but require system updates for LTV-based tiering. Net positive impact on lending capacity.",
        summary: "Housing loan limit raised from Rs 30L to 50L, risk weight reduced to 30% with LTV tiering.",
        deadlines: [],
      },
      {
        type: "ADDED", section: "ESG Risk Integration",
        old: null,
        new: "Banks shall integrate Environmental, Social, and Governance (ESG) risk factors into their ICAAP and credit risk assessment frameworks. Board-level ESG committee to be constituted.",
        risk: "MEDIUM", risk_score: 42,
        risk_breakdown: { compliance: 55, financial: 35, operational: 45, reputational: 40 },
        risk_reasoning: "New ESG integration requirement is forward-looking but requires board restructuring and credit framework modifications. Timeline is flexible.",
        summary: "New ESG risk integration mandate for ICAAP and credit risk. Board-level ESG committee required.",
        deadlines: [],
      },
      {
        type: "MODIFIED", section: "Reporting Frequency",
        old: "Quarterly reporting of capital adequacy through prescribed returns.",
        new: "Monthly reporting of capital adequacy, leverage ratio, and LCR through automated submissions to the RBI portal.",
        risk: "LOW", risk_score: 32,
        risk_breakdown: { compliance: 40, financial: 15, operational: 50, reputational: 10 },
        risk_reasoning: "Increased reporting frequency from quarterly to monthly requires automation investment but limited compliance risk given existing infrastructure.",
        summary: "Reporting changed from quarterly to monthly with automated submission to RBI portal.",
        deadlines: [{ text: "within 90 days", days: 90, urgency: "NORMAL", description: "Updated reporting formats due within 90 days" }],
      },
      {
        type: "ADDED", section: "Climate Stress Testing",
        old: null,
        new: "Banks with assets exceeding Rs 1 lakh crore shall conduct annual climate stress tests covering physical and transition risks, with results disclosed in annual reports.",
        risk: "LOW", risk_score: 28,
        risk_breakdown: { compliance: 35, financial: 25, operational: 30, reputational: 20 },
        risk_reasoning: "Applies only to large banks. Annual frequency allows gradual capability building. Disclosure requirement has limited penalty risk initially.",
        summary: "Annual climate stress testing mandate for banks with assets > Rs 1L Cr, with public disclosure.",
        deadlines: [],
      },
    ],
    mappings: [
      {
        change: { section: "Capital Adequacy Ratio", type: "MODIFIED", risk: "HIGH", summary: "CAR increased from 9% to 11.5%" },
        matched_policies: [
          { policy_id: "POL-CAP-001", policy_title: "Capital Management Policy", score: 0.94, confidence_pct: 94, excerpt: "The bank shall maintain capital adequacy as per RBI norms...", match_explanation: "This policy was selected because it directly governs capital adequacy ratios, CET1 requirements, and capital buffer management — all of which are impacted by the revised CAR threshold." },
          { policy_id: "POL-RISK-003", policy_title: "Risk Appetite Framework", score: 0.87, confidence_pct: 87, excerpt: "Risk appetite shall be set considering regulatory capital requirements...", match_explanation: "This policy was selected because it references regulatory capital thresholds and risk-weighted asset calculations that must be updated to reflect the new 11.5% CAR requirement." },
        ],
        llm_analysis: "The increase in CAR from 9% to 11.5% directly impacts the Capital Management Policy's core thresholds. Section 3.2 on minimum capital ratios and Section 4.1 on capital planning must be updated. The Risk Appetite Framework's risk tolerance bands also need recalibration.",
      },
      {
        change: { section: "Cybersecurity", type: "ADDED", risk: "HIGH", summary: "Cybersecurity incident reporting mandate" },
        matched_policies: [
          { policy_id: "POL-IT-007", policy_title: "IT Security Policy", score: 0.91, confidence_pct: 91, excerpt: "The bank shall maintain cybersecurity incident response procedures...", match_explanation: "This policy was selected because it covers cybersecurity incident management and response timelines, which now need updating to the 6-hour reporting requirement." },
        ],
        llm_analysis: "New cybersecurity reporting requirements mandate 6-hour incident reporting to RBI. The existing IT Security Policy mentions a 24-hour internal escalation window — this must be tightened significantly. A new CISO role needs to be formalized with board-level reporting.",
      },
      {
        change: { section: "IRRBB", type: "MODIFIED", risk: "MEDIUM", summary: "IRRBB framework upgrade" },
        matched_policies: [
          { policy_id: "POL-ALM-002", policy_title: "Asset-Liability Management Policy", score: 0.89, confidence_pct: 89, excerpt: "Interest rate risk shall be managed through gap analysis...", match_explanation: "This policy was selected because it contains the current IRRBB methodology (gap analysis) that must be replaced with the comprehensive EVE/NII framework mandated by the circular." },
        ],
        llm_analysis: "The ALM Policy currently relies on simple gap analysis. The new IRRBB framework requires EVE and NII sensitivity analysis with six prescribed stress scenarios, necessitating a complete methodology overhaul in Sections 5-7 of the policy.",
      },
    ],
    drafts: [
      { change_summary: "CAR increased to 11.5%", policy_id: "POL-CAP-001", policy_title: "Capital Management Policy", risk: "HIGH", draft_update: "Section 3.2 — Minimum Capital Requirements:\n\nThe Bank shall at all times maintain a minimum Capital Adequacy Ratio (CAR) of 11.5% of risk-weighted assets, comprising:\n  a) Common Equity Tier 1 (CET1) capital of not less than 8.0%\n  b) Additional Tier 1 capital as per RBI norms\n  c) Tier 2 capital up to permissible limits\n\nFor banks designated as Domestic Systemically Important Banks (D-SIBs), an additional capital surcharge of 0.6% shall be maintained over and above the minimum CAR.", rationale: "Updated to reflect RBI circular 2025-26/117 revising minimum CAR from 9% to 11.5% and CET1 from 5.5% to 8%, with D-SIB buffer." },
      { change_summary: "Cybersecurity reporting mandate", policy_id: "POL-IT-007", policy_title: "IT Security Policy", risk: "HIGH", draft_update: "Section 8.3 — Incident Reporting:\n\nAll cybersecurity incidents classified as 'Moderate' or above shall be reported to the Reserve Bank of India within six (6) hours of detection, through the prescribed reporting portal.\n\nThe Chief Information Security Officer (CISO) shall:\n  a) Have direct reporting access to the Board of Directors\n  b) Submit quarterly vulnerability assessment reports\n  c) Maintain an updated incident response playbook tested bi-annually", rationale: "New section added per RBI mandate for 6-hour incident reporting and CISO appointment with board-level reporting." },
      { change_summary: "IRRBB framework upgrade", policy_id: "POL-ALM-002", policy_title: "Asset-Liability Management Policy", risk: "MEDIUM", draft_update: "Section 5 — Interest Rate Risk in Banking Book:\n\nThe Bank shall implement a comprehensive IRRBB framework incorporating:\n  a) Economic Value of Equity (EVE) sensitivity analysis\n  b) Net Interest Income (NII) impact assessment\n  c) Monthly stress testing under six prescribed scenarios:\n     i) Parallel shift (+/- 200 bps)\n     ii) Steepening/flattening of yield curve\n     iii) Short-rate shock up/down\n\nResults shall be reported to ALCO monthly and to the Board quarterly.", rationale: "Complete methodology replacement from gap analysis to EVE/NII framework as mandated by revised IRRBB guidelines." },
      { change_summary: "Housing loan risk weight change", policy_id: "POL-RISK-003", policy_title: "Risk Appetite Framework", risk: "MEDIUM", draft_update: "Section 6.4 — Real Estate Exposure Risk Weights:\n\nHousing loans shall carry the following risk weights:\n  a) Loans up to Rs 50 lakh: 30% risk weight\n  b) Loans Rs 50 lakh to Rs 1 crore: 40% risk weight (LTV ≤ 80%)\n  c) Loans exceeding Rs 1 crore: As per existing tiered structure\n\nLoan-to-Value (LTV) ratio shall be the primary determinant for risk weight assignment in the housing segment.", rationale: "Updated to reflect revised risk weight of 30% for housing loans up to Rs 50 lakh with LTV-based tiering mechanism." },
      { change_summary: "Reporting frequency change", policy_id: "POL-REP-004", policy_title: "Regulatory Reporting Policy", risk: "LOW", draft_update: "Section 2.1 — Reporting Schedule:\n\nThe following returns shall be submitted on a monthly basis through automated channels:\n  a) Capital Adequacy Return (CAR)\n  b) Leverage Ratio Return\n  c) Liquidity Coverage Ratio (LCR)\n\nSubmission shall be through the RBI's automated reporting portal within 15 business days of month-end.", rationale: "Updated from quarterly to monthly submission cadence with automated portal submission requirement." },
      { change_summary: "ESG risk integration", policy_id: "NEW", policy_title: "New Policy — ESG Risk Framework", risk: "MEDIUM", draft_update: "ESG Risk Integration Policy:\n\n1. The Bank shall integrate Environmental, Social, and Governance (ESG) risk factors into:\n  a) Internal Capital Adequacy Assessment Process (ICAAP)\n  b) Credit risk assessment frameworks\n  c) Investment screening processes\n\n2. A Board-level ESG Committee shall be constituted, meeting quarterly.\n\n3. ESG risk metrics shall be included in the Risk Appetite Statement.", rationale: "New policy drafted to comply with RBI mandate for ESG integration in risk management frameworks." },
    ],
  };

  renderResults(demo);
  showMsg("msg-run", "✓ Demo data loaded — all 10 features active.", "success");
}
