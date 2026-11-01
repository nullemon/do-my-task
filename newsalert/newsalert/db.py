"""SQLite storage: raw items, stories, alerts, audit log and per-source state.

Single connection, WAL mode, used from the asyncio thread only. Short CLI
processes (stats, mute) open their own connection; WAL lets them read while the
watcher process writes.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .models import RawItem

# Each entry upgrades the schema by one version (PRAGMA user_version).
MIGRATIONS: list[str] = [
    """
    CREATE TABLE items (
        id            INTEGER PRIMARY KEY,
        source        TEXT NOT NULL,
        source_type   TEXT NOT NULL,
        trust         TEXT NOT NULL,
        category      TEXT NOT NULL,
        source_group  TEXT NOT NULL,
        external_id   TEXT,
        url           TEXT,
        url_norm      TEXT,
        account       TEXT,
        title         TEXT NOT NULL,
        text          TEXT NOT NULL,
        text_hash     TEXT NOT NULL,
        published_at  REAL,
        fetched_at    REAL NOT NULL,
        status        TEXT NOT NULL,          -- new | seeded | stale
        story_id      INTEGER REFERENCES stories(id),
        deleted_at    REAL
    );
    CREATE UNIQUE INDEX items_url_norm ON items(url_norm) WHERE url_norm IS NOT NULL;
    CREATE UNIQUE INDEX items_source_ext ON items(source, external_id) WHERE external_id IS NOT NULL;
    CREATE INDEX items_text_hash ON items(text_hash, fetched_at);
    CREATE INDEX items_fetched ON items(fetched_at);

    CREATE TABLE stories (
        id            INTEGER PRIMARY KEY,
        category      TEXT,
        event_type    TEXT,
        subject       TEXT,
        importance    INTEGER,
        is_rumor      INTEGER,
        summary       TEXT,
        confidence    TEXT,
        urgency       TEXT,
        first_item_id INTEGER REFERENCES items(id),
        published_at  REAL,
        fetched_at    REAL,
        triaged_at    REAL,
        alerted_at    REAL,
        created_at    REAL NOT NULL,
        updated_at    REAL
    );
    CREATE INDEX stories_created ON stories(created_at);

    CREATE TABLE alerts (
        id         INTEGER PRIMARY KEY,
        story_id   INTEGER REFERENCES stories(id),
        kind       TEXT NOT NULL,             -- ring | followup | health | test
        urgency    TEXT,
        channel    TEXT,
        title      TEXT,
        message    TEXT,
        created_at REAL NOT NULL,
        sent_at    REAL,
        ok         INTEGER,
        error      TEXT
    );

    CREATE TABLE audit_log (
        id     INTEGER PRIMARY KEY,
        ts     REAL NOT NULL,
        event  TEXT NOT NULL,
        detail TEXT
    );

    CREATE TABLE source_state (
        source               TEXT PRIMARY KEY,
        etag                 TEXT,
        last_modified        TEXT,
        seeded               INTEGER NOT NULL DEFAULT 0,
        last_success_at      REAL,
        last_error_at        REAL,
        last_error           TEXT,
        failing_since        REAL,
        consecutive_failures INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE kv (
        key   TEXT PRIMARY KEY,
        value TEXT
    );
    """,
]

_SOURCE_STATE_FIELDS = {
    "etag",
    "last_modified",
    "seeded",
    "last_success_at",
    "last_error_at",
    "last_error",
    "failing_since",
    "consecutive_failures",
}


class Database:
    def __init__(self, path: str | Path) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        for i, script in enumerate(MIGRATIONS[version:], start=version + 1):
            self.conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version={i};\nCOMMIT;")

    # ------------------------------------------------------------------ items

    def find_duplicate(
        self,
        *,
        source: str,
        external_id: str | None,
        url_norm: str | None,
        text_hash: str | None,
        text_since: float,
    ) -> str | None:
        """Return why this item is a duplicate (or None if it is new)."""
        c = self.conn
        if external_id and c.execute(
            "SELECT 1 FROM items WHERE source=? AND external_id=?", (source, external_id)
        ).fetchone():
            return "external_id"
        if url_norm and c.execute("SELECT 1 FROM items WHERE url_norm=?", (url_norm,)).fetchone():
            return "url"
        if text_hash and c.execute(
            "SELECT 1 FROM items WHERE text_hash=? AND fetched_at>=?", (text_hash, text_since)
        ).fetchone():
            return "text"
        return None

    def insert_item(self, item: RawItem, *, url_norm: str | None, text_hash: str, status: str) -> int | None:
        """Insert a raw item. Returns its id, or None if a unique index rejected it."""
        try:
            cur = self.conn.execute(
                """INSERT INTO items (source, source_type, trust, category, source_group,
                       external_id, url, url_norm, account, title, text, text_hash,
                       published_at, fetched_at, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    item.source,
                    item.source_type,
                    item.trust,
                    item.category,
                    item.source_group,
                    item.external_id,
                    item.url,
                    url_norm,
                    item.account,
                    item.title,
                    item.text,
                    text_hash,
                    item.published_at,
                    item.fetched_at,
                    status,
                ),
            )
        except sqlite3.IntegrityError:
            return None
        return cur.lastrowid

    def recent_items(self, limit: int = 20, status: str | None = None) -> list[sqlite3.Row]:
        if status:
            return self.conn.execute(
                "SELECT * FROM items WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit)
            ).fetchall()
        return self.conn.execute("SELECT * FROM items ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def item_counts(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT status, COUNT(*) AS n FROM items GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}

    # ------------------------------------------------------------------ source state

    def get_source_state(self, source: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM source_state WHERE source=?", (source,)).fetchone()
        if row is None:
            return {"source": source, "seeded": 0, "consecutive_failures": 0}
        return dict(row)

    def update_source_state(self, source: str, **fields: Any) -> None:
        unknown = set(fields) - _SOURCE_STATE_FIELDS
        if unknown:
            raise ValueError(f"unknown source_state fields: {unknown}")
        self.conn.execute("INSERT OR IGNORE INTO source_state (source) VALUES (?)", (source,))
        if fields:
            cols = ", ".join(f"{k}=?" for k in fields)
            self.conn.execute(f"UPDATE source_state SET {cols} WHERE source=?", (*fields.values(), source))

    def all_source_states(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM source_state ORDER BY source").fetchall()

    # ------------------------------------------------------------------ audit / kv

    def audit(self, event: str, **detail: Any) -> None:
        self.conn.execute(
            "INSERT INTO audit_log (ts, event, detail) VALUES (?,?,?)",
            (time.time(), event, json.dumps(detail, default=str, ensure_ascii=False)),
        )

    def kv_get(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def kv_set(self, key: str, value: str | None) -> None:
        if value is None:
            self.conn.execute("DELETE FROM kv WHERE key=?", (key,))
        else:
            self.conn.execute(
                "INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
