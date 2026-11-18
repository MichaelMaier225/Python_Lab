from contextlib import closing
import hashlib
from http.client import HTTPException, HTTPSConnection
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from .database import DB_PATH


def pair_id(a, b):
    # Ignore transient database row IDs; use complete submitted listing contents.
    listings = [json.dumps(p, sort_keys=True, ensure_ascii=False) for p in (a, b)]
    return hashlib.sha256("\n".join(sorted(listings)).encode()).hexdigest()


class FeedbackStorageError(RuntimeError):
    pass


def supabase_request(host, key, method, query, row=None):
    headers = {"apikey": key, "Accept": "application/json"}
    body = None
    if row is not None:
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "resolution=ignore-duplicates,return=representation"
        body = json.dumps(row, allow_nan=False).encode()
    try:
        with closing(HTTPSConnection(host, timeout=5)) as conn:
            conn.request(method, "/rest/v1/feedback?" + query, body=body, headers=headers)
            response = conn.getresponse()
            if not 200 <= response.status < 300:
                raise FeedbackStorageError(f"Supabase returned HTTP {response.status}.")
            rows = json.load(response)
            if not isinstance(rows, list):
                raise FeedbackStorageError("Unexpected Supabase response.")
            return rows
    except (OSError, HTTPException, ValueError) as exc:
        raise FeedbackStorageError("Could not complete the Supabase request.") from exc


def save_to_supabase(url, key, row):
    project = re.fullmatch(r"https://([a-z0-9]+\.supabase\.co)/?", url)
    if not project or not key.startswith("sb_secret_"):
        raise FeedbackStorageError("Supabase feedback configuration is incomplete or invalid.")
    host = project.group(1)
    if supabase_request(host, key, "POST", "on_conflict=request_id", row):
        return False

    request_id = UUID(row["request_id"])
    existing = supabase_request(
        host, key, "GET", f"request_id=eq.{request_id}&select=pair_id,choice,record"
    )
    if len(existing) != 1:
        raise FeedbackStorageError("Could not verify the existing review.")
    if existing[0] != {name: row[name] for name in ("pair_id", "choice", "record")}:
        raise ValueError("This submission identifier was already used for different feedback.")
    return True


def save_feedback(a, b, prediction, choice, request_id):
    row = {
        "request_id": request_id,
        "pair_id": pair_id(a, b),
        "model_id": prediction["model_id"],
        "model_version": prediction["model_version"],
        "choice": choice,
        "record": {"product_a": a, "product_b": b, "prediction": prediction},
    }
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    duplicate = save_to_supabase(url, key, row) if url or key else save_to_sqlite(row)
    return {"saved": True, "duplicate": duplicate, "pair_id": row["pair_id"]}


def save_to_sqlite(row):
    directory = Path(os.getenv("PRODUCTMATCH_FEEDBACK_DIR") or DB_PATH.parent)
    path = directory / "feedback.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = json.dumps(row["record"], sort_keys=True)
    request_id, identifier, choice = (row[name] for name in ("request_id", "pair_id", "choice"))
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
            request_id TEXT PRIMARY KEY, pair_id TEXT NOT NULL,
            model_id TEXT NOT NULL, model_version TEXT NOT NULL,
            choice TEXT NOT NULL, record TEXT NOT NULL, created_at TEXT NOT NULL
        )""")
        inserted = conn.execute("""
            INSERT INTO feedback
                (request_id, pair_id, model_id, model_version, choice, record, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(request_id) DO NOTHING
        """, (
            request_id, identifier, row["model_id"], row["model_version"], choice,
            record, datetime.now(timezone.utc).isoformat()
        ))
        duplicate = inserted.rowcount == 0
        if duplicate:
            existing = conn.execute(
                "SELECT pair_id, choice, record FROM feedback WHERE request_id = ?", (request_id,)
            ).fetchone()
            if existing != (identifier, choice, record):
                raise ValueError("This submission identifier was already used for different feedback.")
    return duplicate
