"""
orchestrator/workflow.py
─────────────────────────────────────────────────────────────────────────────
LangGraph Orchestrator — Stateful multi-agent workflow graph.

Graph topology:
  [START]
     ↓
  parser  →  diff  →  risk_scorer  →  mapper  →  explainer
                                                      ↓
                                         drafter  →  deadline_tracker
                                                      ↓
                                                   reporter
                                                      ↓
                                                    [END]
─────────────────────────────────────────────────────────────────────────────
"""

from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()

# Import agent runners
from agents import parser, diff, mapper, drafter, reporter
from agents import risk_scorer, deadline_tracker, explainer


# ── Shared State Schema ───────────────────────────────────────────────────────

class ComplianceState(TypedDict, total=False):
    # Input fields
    file_path:    str           # Path to new regulatory PDF
    old_text:     str           # Previous version text (may be empty)
    source:       str           # "rbi" | "sebi" | "manual"

    # Parser output
    full_text:    str
    chunks:       list[str]
    doc_metadata: dict[str, Any]

    # Diff output
    changes:      list[dict]

    # Mapper output
    mappings:     list[dict]

    # Drafter output
    drafts:       list[dict]

    # Reporter output
    report_html:  str
    report_json:  dict
    report_path:  str

    # Advanced features
    all_deadlines: list[dict]   # Deadline tracker output

    # Error handling
    error:        Optional[str]


# ── Agent node wrappers ───────────────────────────────────────────────────────

def _parser_node(state: ComplianceState) -> ComplianceState:
    print("\n" + "─" * 60)
    print("🔵 [Orchestrator] Running: Parser Agent")
    return parser.run(state)


def _diff_node(state: ComplianceState) -> ComplianceState:
    print("\n" + "─" * 60)
    print("🔵 [Orchestrator] Running: Diff Agent")
    return diff.run(state)


def _risk_scorer_node(state: ComplianceState) -> ComplianceState:
    print("\n" + "─" * 60)
    print("🔵 [Orchestrator] Running: Risk Scoring Engine")
    return risk_scorer.run(state)


def _mapper_node(state: ComplianceState) -> ComplianceState:
    print("\n" + "─" * 60)
    print("🔵 [Orchestrator] Running: Mapper Agent (RAG)")
    return mapper.run(state)


def _explainer_node(state: ComplianceState) -> ComplianceState:
    print("\n" + "─" * 60)
    print("🔵 [Orchestrator] Running: Explainability Layer")
    return explainer.enrich_mappings(state)


def _drafter_node(state: ComplianceState) -> ComplianceState:
    print("\n" + "─" * 60)
    print("🔵 [Orchestrator] Running: Drafter Agent")
    return drafter.run(state)


def _deadline_node(state: ComplianceState) -> ComplianceState:
    print("\n" + "─" * 60)
    print("🔵 [Orchestrator] Running: Deadline Tracker")
    return deadline_tracker.run(state)


def _reporter_node(state: ComplianceState) -> ComplianceState:
    print("\n" + "─" * 60)
    print("🔵 [Orchestrator] Running: Report Agent")
    return reporter.run(state)


# ── Conditional edge: skip on error ──────────────────────────────────────────

def _should_continue(state: ComplianceState) -> str:
    if state.get("error"):
        print(f"❌ [Orchestrator] Pipeline halted: {state['error']}")
        return END
    return "diff"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """Construct and compile the LangGraph workflow."""
    graph = StateGraph(ComplianceState)

    # Register nodes
    graph.add_node("parser",        _parser_node)
    graph.add_node("diff",          _diff_node)
    graph.add_node("risk_scorer",   _risk_scorer_node)
    graph.add_node("mapper",        _mapper_node)
    graph.add_node("explainer",     _explainer_node)
    graph.add_node("drafter",       _drafter_node)
    graph.add_node("deadline",      _deadline_node)
    graph.add_node("reporter",      _reporter_node)

    # Entry point
    graph.add_edge(START, "parser")

    # Conditional: stop early if parser fails
    graph.add_conditional_edges("parser", _should_continue, {
        "diff": "diff",
        END:    END,
    })

    # Enhanced flow with new agents
    graph.add_edge("diff",          "risk_scorer")
    graph.add_edge("risk_scorer",   "mapper")
    graph.add_edge("mapper",        "explainer")
    graph.add_edge("explainer",     "drafter")
    graph.add_edge("drafter",       "deadline")
    graph.add_edge("deadline",      "reporter")
    graph.add_edge("reporter",      END)

    return graph.compile()


# ── Public entry-point ────────────────────────────────────────────────────────

def run_pipeline(file_path: str, old_text: str = "") -> dict[str, Any]:
    """
    Execute the full compliance pipeline and return the final state.

    Parameters
    ----------
    file_path : str  — absolute path to the regulatory PDF
    old_text  : str  — text of the previous version (empty = first upload)
    """
    print("\n" + "=" * 60)
    print("🚀 [Orchestrator] Compliance pipeline STARTED")
    print(f"   PDF     : {file_path}")
    print(f"   Baseline: {'provided' if old_text.strip() else 'none (first upload)'}")
    print(f"   Agents  : parser → diff → risk_scorer → mapper → explainer → drafter → deadline → reporter")
    print("=" * 60)

    workflow = build_workflow()

    initial_state: ComplianceState = {
        "file_path": file_path,
        "old_text":  old_text,
        "source":    "manual",
    }

    final_state = workflow.invoke(initial_state)

    print("\n" + "=" * 60)
    print("✅ [Orchestrator] Pipeline COMPLETE")
    print(f"   Report saved: {final_state.get('report_path', 'N/A')}")
    print(f"   Deadlines found: {len(final_state.get('all_deadlines', []))}")
    print("=" * 60 + "\n")

    return final_state
