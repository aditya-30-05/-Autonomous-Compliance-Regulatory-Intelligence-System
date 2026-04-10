"""
scripts/setup.py
─────────────────────────────────────────────────────────────────────────────
One-shot setup script:
  1. Creates all required directories
  2. Copies .env.example → .env (if not exists)
  3. Loads sample policies into ChromaDB
  4. Generates demo PDFs

Usage:
    python scripts/setup.py
─────────────────────────────────────────────────────────────────────────────
"""

import os
import shutil
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


def main():
    print("=" * 55)
    print("  ComplianceAI — One-Shot Setup")
    print("=" * 55)

    root = Path(__file__).parent.parent

    # ── 1. Directories ─────────────────────────────────────────
    dirs = [
        root / "data" / "uploads",
        root / "data" / "reports",
        root / "data" / "policies",
        root / "data" / "demo",
        root / "db" / "chroma_store",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("✅  Directories created")

    # ── 2. .env ────────────────────────────────────────────────
    env_file    = root / ".env"
    env_example = root / ".env.example"
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅  .env created from .env.example (set your OPENAI_API_KEY!)")
    else:
        print("ℹ️   .env already exists")

    # ── 3. Load policies ───────────────────────────────────────
    print("\n📦 Loading policies into ChromaDB…")
    try:
        from utils.policy_loader import load_policies
        count = load_policies(reset=False)
        print(f"✅  {count} chunk(s) loaded into ChromaDB")
    except Exception as e:
        print(f"⚠️  Policy load failed: {e}")

    # ── 4. Demo PDFs ───────────────────────────────────────────
    print("\n📄 Generating demo PDFs…")
    try:
        from scripts.generate_demo_pdf import generate
        generate()
    except Exception as e:
        print(f"⚠️  Demo PDF generation failed: {e}")

    print("\n" + "=" * 55)
    print("  Setup complete! Next steps:")
    print("  1. Edit .env → set OPENAI_API_KEY")
    print("  2. Run:  uvicorn api.main:app --reload")
    print("  3. Open: frontend/index.html")
    print("=" * 55)


if __name__ == "__main__":
    main()
