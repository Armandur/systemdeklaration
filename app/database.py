"""SQLite-lager. En deklaration = metadata + JSON-payload (det fasta
skelettet med ifyllda värden)."""
import json
import sqlite3
import time
from contextlib import contextmanager

from . import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS declarations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )


def list_declarations() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, created_at, updated_at FROM declarations ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_declaration(dec_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM declarations WHERE id = ?", (dec_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["payload"] = json.loads(d["payload"])
    return d


def create_declaration(name: str, payload: dict) -> int:
    now = int(time.time())
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO declarations (name, payload, created_at, updated_at) VALUES (?,?,?,?)",
            (name, json.dumps(payload, ensure_ascii=False), now, now),
        )
        return cur.lastrowid


def update_declaration(dec_id: int, name: str, payload: dict) -> None:
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "UPDATE declarations SET name = ?, payload = ?, updated_at = ? WHERE id = ?",
            (name, json.dumps(payload, ensure_ascii=False), now, dec_id),
        )


def delete_declaration(dec_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM declarations WHERE id = ?", (dec_id,))
