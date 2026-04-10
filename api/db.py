import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

DB_PATH = Path("data/sessions.sqlite")

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                new_path TEXT,
                old_path TEXT,
                result TEXT,
                created_at TEXT,
                completed_at TEXT
            )
        """)

def create_session(session_id: str, new_path: str, old_path: Optional[str] = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO sessions (id, new_path, old_path, created_at) VALUES (?, ?, ?, ?)",
            (session_id, new_path, old_path, datetime.now().isoformat())
        )

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "new_path": row["new_path"],
            "old_path": row["old_path"],
            "result": json.loads(row["result"]) if row["result"] else None,
            "created_at": row["created_at"],
            "completed_at": row["completed_at"]
        }

def update_session_result(session_id: str, result: Dict[str, Any]):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE sessions SET result = ?, completed_at = ? WHERE id = ?",
            (json.dumps(result), datetime.now().isoformat(), session_id)
        )

init_db()
