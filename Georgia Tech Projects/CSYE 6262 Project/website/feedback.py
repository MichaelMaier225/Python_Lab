import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from .database import DB_PATH


def pair_id(a, b):
    # Ignore transient database row IDs; use complete submitted listing contents.
    listings = [json.dumps(p, sort_keys=True, ensure_ascii=False) for p in (a, b)]
    return hashlib.sha256("\n".join(sorted(listings)).encode()).hexdigest()


def save_feedback(a, b, prediction, choice, request_id):
    path = DB_PATH.parent / "feedback.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    identifier = pair_id(a, b)
    record = json.dumps({"product_a": a, "product_b": b, "prediction": prediction}, sort_keys=True)
    with sqlite3.connect(path) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
            request_id TEXT PRIMARY KEY, pair_id TEXT NOT NULL,
            model_id TEXT NOT NULL, model_version TEXT NOT NULL,
            choice TEXT NOT NULL, record TEXT NOT NULL, created_at TEXT NOT NULL
        )""")
        old = conn.execute("SELECT pair_id, choice, record FROM feedback WHERE request_id = ?", (request_id,)).fetchone()
        if old:
            if old != (identifier, choice, record):
                raise ValueError("This submission identifier was already used for different feedback.")
            return {"saved": True, "duplicate": True, "pair_id": identifier}
        conn.execute("INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?, ?)", (
            request_id, identifier, prediction["model_id"], prediction["model_version"], choice,
            record, datetime.now(timezone.utc).isoformat()
        ))
    return {"saved": True, "duplicate": False, "pair_id": identifier}
