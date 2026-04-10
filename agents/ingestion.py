"""
agents/ingestion.py
─────────────────────────────────────────────────────────────────────────────
Ingestion Agent (Optional) — Scrapes RBI/SEBI regulatory websites for new
circular links. Falls back gracefully if scraping fails.

Input  (JSON): { "source": "rbi" | "sebi" | "manual" }
Output (JSON): { "pdf_links": [ { "title": str, "url": str } ] }
─────────────────────────────────────────────────────────────────────────────
"""

from typing import Any
import requests
from bs4 import BeautifulSoup

# ── Source configs ─────────────────────────────────────────────────────────────

SOURCES = {
    "rbi": {
        "url": "https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Type=1",
        "link_selector": "a[href*='.pdf'], a[href*='Notification']",
        "base": "https://www.rbi.org.in",
    },
    "sebi": {
        "url": "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=3&smid=0&pageno=1",
        "link_selector": "a[href*='.pdf']",
        "base": "https://www.sebi.gov.in",
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0 Safari/537.36"
    )
}


def _scrape(source_key: str) -> list[dict]:
    cfg = SOURCES.get(source_key)
    if not cfg:
        return []

    try:
        resp = requests.get(cfg["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[IngestionAgent] ⚠️  Could not reach {cfg['url']}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    links = []

    for tag in soup.select(cfg["link_selector"])[:20]:
        href  = tag.get("href", "")
        title = tag.get_text(strip=True) or "Circular"
        if href and not href.startswith("http"):
            href = cfg["base"].rstrip("/") + "/" + href.lstrip("/")
        if href:
            links.append({"title": title, "url": href})

    return links


# ── Public API ─────────────────────────────────────────────────────────────────

def run(state: dict[str, Any]) -> dict[str, Any]:
    """
    Ingestion Agent entry-point.

    State keys consumed
    -------------------
    source : str  — "rbi" | "sebi" | "manual"
    """
    source: str = state.get("source", "rbi").lower()

    if source == "manual":
        print("[IngestionAgent] 📁  Manual upload mode — skipping web scrape.")
        return {**state, "pdf_links": []}

    print(f"[IngestionAgent] 🌐  Scraping {source.upper()} website…")
    pdf_links = _scrape(source)

    print(f"[IngestionAgent] ✅  Found {len(pdf_links)} link(s) on {source.upper()}.")
    return {**state, "pdf_links": pdf_links}
