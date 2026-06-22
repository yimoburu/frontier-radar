from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
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
                    outputs_json TEXT NOT NULL,
                    job_type TEXT NOT NULL DEFAULT 'daily',
                    effective_config_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS source_runs (
                    source_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    error TEXT NOT NULL,
                    retry_eligible INTEGER NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS run_locks (
                    name TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    acquired_at TEXT NOT NULL
                );
                """
            )
            self._migrate_runs(conn)

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

    def item_ids(self) -> set[str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT item_id FROM items").fetchall()
        return {str(row["item_id"]) for row in rows}

    def record_run(
        self,
        started_at: str,
        finished_at: str,
        status: str,
        counts: dict[str, int],
        errors: list[str],
        outputs: list[str],
        job_type: str = "daily",
        effective_config: dict[str, Any] | None = None,
    ) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO runs (
                    started_at, finished_at, status, counts_json, errors_json,
                    outputs_json, job_type, effective_config_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    started_at,
                    finished_at,
                    status,
                    json.dumps(counts, sort_keys=True),
                    json.dumps(errors, sort_keys=True),
                    json.dumps(outputs, sort_keys=True),
                    job_type,
                    json.dumps(effective_config or {}, sort_keys=True),
                ),
            )
            return int(cursor.lastrowid)

    def record_source_run(
        self,
        run_id: int,
        source: str,
        status: str,
        count: int,
        error: str = "",
        retry_eligible: bool = False,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO source_runs (run_id, source, status, count, error, retry_eligible)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, source, status, count, error, int(retry_eligible)),
            )

    def source_runs_for_run(self, run_id: int) -> dict[str, dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM source_runs WHERE run_id = ? ORDER BY source ASC",
                (run_id,),
            ).fetchall()
        return {
            row["source"]: {
                "source_run_id": row["source_run_id"],
                "run_id": row["run_id"],
                "source": row["source"],
                "status": row["status"],
                "count": row["count"],
                "error": row["error"],
                "retry_eligible": bool(row["retry_eligible"]),
            }
            for row in rows
        }

    def latest_run(self, job_type: str | None = None) -> dict[str, Any] | None:
        query = "SELECT * FROM runs"
        params: tuple[Any, ...] = ()
        if job_type is not None:
            query += " WHERE job_type = ?"
            params = (job_type,)
        query += " ORDER BY run_id DESC LIMIT 1"

        with self.connect() as conn:
            row = conn.execute(query, params).fetchone()

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
            "job_type": row["job_type"],
            "effective_config": json.loads(row["effective_config_json"]),
        }

    def acquire_lock(
        self,
        name: str,
        job_type: str,
        acquired_at: str,
        stale_after_minutes: int,
    ) -> bool:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM run_locks WHERE name = ?", (name,)).fetchone()
            if row is not None:
                if not _is_stale(row["acquired_at"], acquired_at, stale_after_minutes):
                    return False
                conn.execute("DELETE FROM run_locks WHERE name = ?", (name,))
            conn.execute(
                "INSERT INTO run_locks (name, job_type, acquired_at) VALUES (?, ?, ?)",
                (name, job_type, acquired_at),
            )
            return True

    def release_lock(self, name: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM run_locks WHERE name = ?", (name,))

    def active_locks(self) -> list[dict[str, str]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM run_locks ORDER BY name ASC").fetchall()
        return [
            {"name": row["name"], "job_type": row["job_type"], "acquired_at": row["acquired_at"]}
            for row in rows
        ]

    def cleanup_stale_locks(self, now: str, stale_after_minutes: int) -> list[str]:
        cleaned: list[str] = []
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM run_locks ORDER BY name ASC").fetchall()
            for row in rows:
                if _is_stale(row["acquired_at"], now, stale_after_minutes):
                    conn.execute("DELETE FROM run_locks WHERE name = ?", (row["name"],))
                    cleaned.append(row["name"])
        return cleaned

    def integrity_check(self) -> str:
        with self.connect() as conn:
            row = conn.execute("PRAGMA integrity_check").fetchone()
        return str(row[0])

    def vacuum(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        try:
            conn.execute("VACUUM")
        finally:
            conn.close()

    def duplicate_candidates(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT url, COUNT(*) AS count
                FROM items
                GROUP BY url
                HAVING COUNT(*) > 1
                ORDER BY count DESC, url ASC
                """
            ).fetchall()
        return [{"url": row["url"], "count": row["count"]} for row in rows]

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

    def _migrate_runs(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
        if "job_type" not in columns:
            conn.execute("ALTER TABLE runs ADD COLUMN job_type TEXT NOT NULL DEFAULT 'daily'")
        if "effective_config_json" not in columns:
            conn.execute("ALTER TABLE runs ADD COLUMN effective_config_json TEXT NOT NULL DEFAULT '{}'")


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_stale(acquired_at: str, now: str, stale_after_minutes: int) -> bool:
    age = _parse_time(now) - _parse_time(acquired_at)
    return age.total_seconds() >= stale_after_minutes * 60
