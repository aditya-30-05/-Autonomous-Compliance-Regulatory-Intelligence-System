"""
utils/policy_loader.py
─────────────────────────────────────────────────────────────────────────────
Loads sample / real policy documents into ChromaDB on first run.

Usage:
    python -m utils.policy_loader          # load all files from POLICIES_DIR
    python -m utils.policy_loader --reset  # wipe collection and reload
─────────────────────────────────────────────────────────────────────────────
"""

import argparse
import os
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

POLICIES_DIR = os.getenv("POLICIES_DIR", "./data/policies")
CHROMA_DIR   = os.getenv("CHROMA_PERSIST_DIR", "./db/chroma_store")
COLLECTION   = os.getenv("CHROMA_COLLECTION_NAME", "company_policies")
CHUNK_SIZE   = int(os.getenv("CHUNK_SIZE", 700))
CHUNK_OVERLAP= int(os.getenv("CHUNK_OVERLAP", 100))


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def load_policies(reset: bool = False) -> int:
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    emb_fn = embedding_functions.DefaultEmbeddingFunction()

    if reset:
        try:
            client.delete_collection(COLLECTION)
            print(f"[PolicyLoader] 🗑️  Collection '{COLLECTION}' wiped.")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=emb_fn,
    )

    policy_dir = Path(POLICIES_DIR)
    policy_dir.mkdir(parents=True, exist_ok=True)
    txt_files = list(policy_dir.glob("*.txt"))

    if not txt_files:
        print(f"[PolicyLoader] ⚠️  No .txt files found in {POLICIES_DIR}")
        return 0

    total_chunks = 0
    for fpath in txt_files:
        policy_id    = fpath.stem                         # e.g. "kyc_policy"
        policy_title = policy_id.replace("_", " ").title()
        text = fpath.read_text(encoding="utf-8")
        chunks = _chunk_text(text)

        ids       = [f"{policy_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {"policy_id": policy_id, "policy_title": policy_title,
             "chunk_index": i, "source_file": str(fpath)}
            for i in range(len(chunks))
        ]

        # Upsert (skip if already present)
        existing_ids = set(collection.get(ids=ids)["ids"])
        new_ids   = [i for i in ids if i not in existing_ids]
        new_docs  = [chunks[ids.index(i)] for i in new_ids]
        new_metas = [metadatas[ids.index(i)] for i in new_ids]

        if new_ids:
            collection.add(documents=new_docs, metadatas=new_metas, ids=new_ids)

        total_chunks += len(new_ids)
        print(f"[PolicyLoader] ✅  '{policy_title}' → {len(new_ids)} new chunk(s)")

    print(f"[PolicyLoader] 📦  Total chunks in collection: {collection.count()}")
    return total_chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="Wipe collection before loading")
    args = parser.parse_args()
    load_policies(reset=args.reset)
