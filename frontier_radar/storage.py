from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from frontier_radar.models import NormalizedItem


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS items (
                    item_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    author TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    raw_path TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    counts_json TEXT NOT NULL,
                    errors_json TEXT NOT NULL,
                    outputs_json TEXT NOT NULL
                );
                """
            )

    def upsert_items(self, items: list[NormalizedItem]) -> None:
        with self.connect() as conn:
            for item in items:
                record = item.to_record()
                conn.execute(
                    """
                    INSERT INTO items (
                        item_id, source, source_type, title, url, author, published_at,
                        summary, raw_path, tags_json, metrics_json, metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        source=excluded.source,
                        source_type=excluded.source_type,
                        title=excluded.title,
                        author=excluded.author,
                        published_at=excluded.published_at,
                        summary=excluded.summary,
                        raw_path=excluded.raw_path,
                        tags_json=excluded.tags_json,
                        metrics_json=excluded.metrics_json,
                        metadata_json=excluded.metadata_json,
                        last_seen_at=CURRENT_TIMESTAMP
                    """,
                    (
                        record["item_id"],
                        record["source"],
                        record["source_type"],
                        record["title"],
                        record["url"],
                        record["author"],
                        record["published_at"],
                        record["summary"],
                        record["raw_path"],
                        json.dumps(record["tags"], sort_keys=True),
                        json.dumps(record["metrics"], sort_keys=True),
                        json.dumps(record["metadata"], sort_keys=True),
                    ),
                )

    def list_items(self, limit: int | None = None) -> list[NormalizedItem]:
        query = "SELECT * FROM items ORDER BY published_at DESC, title ASC"
        params: tuple[Any, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_item(row) for row in rows]

    def record_run(
        self,
        started_at: str,
        finished_at: str,
        status: str,
        counts: dict[str, int],
        errors: list[str],
        outputs: list[str],
    ) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO runs (started_at, finished_at, status, counts_json, errors_json, outputs_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    started_at,
                    finished_at,
                    status,
                    json.dumps(counts, sort_keys=True),
                    json.dumps(errors, sort_keys=True),
                    json.dumps(outputs, sort_keys=True),
                ),
            )
            return int(cursor.lastrowid)

    def latest_run(self) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM runs ORDER BY run_id DESC LIMIT 1").fetchone()

        if row is None:
            return None

        return {
            "run_id": row["run_id"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "status": row["status"],
            "counts": json.loads(row["counts_json"]),
            "errors": json.loads(row["errors_json"]),
            "outputs": json.loads(row["outputs_json"]),
        }

    def _row_to_item(self, row: sqlite3.Row) -> NormalizedItem:
        return NormalizedItem(
            source=row["source"],
            source_type=row["source_type"],
            title=row["title"],
            url=row["url"],
            author=row["author"],
            published_at=row["published_at"],
            summary=row["summary"],
            raw_path=row["raw_path"],
            tags=json.loads(row["tags_json"]),
            metrics=json.loads(row["metrics_json"]),
            metadata=json.loads(row["metadata_json"]),
        )
