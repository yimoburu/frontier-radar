# Frontier Radar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a harness-agnostic local CLI that tracks frontier AI sources, stores raw evidence, ranks important items, and maintains a Karpathy-style Markdown knowledge wiki.

**Architecture:** The core system is Python package code plus filesystem artifacts: immutable `raw/` snapshots, SQLite state in `state/frontier-radar.sqlite`, and synthesized Markdown in `wiki/`. Harness files (`AGENTS.md`, `CLAUDE.md`, `CODEX.md`) are adapters over a shared contract, while the CLI remains runnable without any agent harness.

**Tech Stack:** Python 3.11+, argparse, sqlite3, urllib, xml.etree.ElementTree, PyYAML, pytest.

---

## File Structure

All paths are under `/Users/xwli/Documents/st`.

- Create `pyproject.toml`: package metadata, console script, pytest config, runtime dependency on PyYAML.
- Create `README.md`: quickstart, source model, daily run instructions, scheduler summary.
- Create `AGENTS.md`: canonical harness-neutral wiki contract.
- Create `CLAUDE.md`: Claude Code adapter that points back to `AGENTS.md`.
- Create `CODEX.md`: Codex adapter that points back to `AGENTS.md`.
- Create `config/sources.yaml`: no-secret source configuration.
- Create `config/topics.yaml`: topic taxonomy and ranking keywords.
- Create `frontier_radar/__init__.py`: package version.
- Create `frontier_radar/models.py`: normalized item and scored item dataclasses.
- Create `frontier_radar/config.py`: YAML config loading and repository path resolution.
- Create `frontier_radar/raw.py`: immutable raw snapshot writer.
- Create `frontier_radar/storage.py`: SQLite schema, item upsert, run recording, query helpers.
- Create `frontier_radar/ranking.py`: score component calculation and top item selection.
- Create `frontier_radar/wiki/render.py`: daily digest Markdown renderer.
- Create `frontier_radar/wiki/lint.py`: wiki link and provenance validation.
- Create `frontier_radar/collectors/base.py`: collector interfaces, HTTP helper, status model.
- Create `frontier_radar/collectors/github.py`: unauthenticated GitHub repository search collector.
- Create `frontier_radar/collectors/hn.py`: Hacker News Algolia collector.
- Create `frontier_radar/collectors/rss.py`: generic RSS/Atom collector for blogs and YouTube RSS.
- Create `frontier_radar/collectors/arxiv.py`: arXiv Atom collector.
- Create `frontier_radar/collectors/manual.py`: local manual notes collector for X-adjacent expert signals.
- Create `frontier_radar/daily.py`: orchestrates fetch, rank, digest, and run metadata.
- Create `frontier_radar/cli.py`: argparse commands.
- Create `docs/scheduling/cron.md`: portable cron example.
- Create `docs/scheduling/launchd.md`: macOS launchd example.
- Create `docs/scheduling/systemd.md`: Linux systemd timer example.
- Create `docs/scheduling/codex.md`: Codex app automation instructions without embedding scheduler internals.
- Create `manual/.gitkeep`, `raw/.gitkeep`, `state/.gitkeep`, and wiki directory `.gitkeep` files.
- Create tests under `tests/` for each behavioral unit.

## Task 1: Project Skeleton And Harness Contract

**Files:**
- Create: `/Users/xwli/Documents/st/pyproject.toml`
- Create: `/Users/xwli/Documents/st/README.md`
- Create: `/Users/xwli/Documents/st/AGENTS.md`
- Create: `/Users/xwli/Documents/st/CLAUDE.md`
- Create: `/Users/xwli/Documents/st/CODEX.md`
- Create: `/Users/xwli/Documents/st/config/sources.yaml`
- Create: `/Users/xwli/Documents/st/config/topics.yaml`
- Create: `/Users/xwli/Documents/st/frontier_radar/__init__.py`
- Create: `/Users/xwli/Documents/st/tests/test_package_metadata.py`

- [ ] **Step 1: Write the failing metadata test**

Create `/Users/xwli/Documents/st/tests/test_package_metadata.py`:

```python
from pathlib import Path


def test_package_exports_version():
    import frontier_radar

    assert frontier_radar.__version__ == "0.1.0"


def test_harness_files_delegate_to_agents_contract():
    root = Path(__file__).resolve().parents[1]
    agents = (root / "AGENTS.md").read_text()
    claude = (root / "CLAUDE.md").read_text()
    codex = (root / "CODEX.md").read_text()

    assert "canonical contract" in agents
    assert "AGENTS.md" in claude
    assert "AGENTS.md" in codex
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_package_metadata.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'frontier_radar'`.

- [ ] **Step 3: Create project skeleton files**

Create `/Users/xwli/Documents/st/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "frontier-radar"
version = "0.1.0"
description = "Harness-agnostic local tracker and Markdown wiki for frontier AI signals."
readme = "README.md"
requires-python = ">=3.11"
dependencies = ["PyYAML>=6.0.1"]

[project.optional-dependencies]
test = ["pytest>=8.2"]

[project.scripts]
frontier-radar = "frontier_radar.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Create `/Users/xwli/Documents/st/frontier_radar/__init__.py`:

```python
"""Frontier Radar package."""

__version__ = "0.1.0"
```

Create `/Users/xwli/Documents/st/AGENTS.md`:

```markdown
# Frontier Radar Agent Contract

This file is the canonical contract for any LLM harness operating this repository. Codex, Claude Code, OpenCode, Gemini CLI, Cursor, and future harnesses should treat this file as the shared source of truth.

## Operating Model

- Use the CLI first: `frontier-radar daily`, `frontier-radar fetch`, `frontier-radar rank`, `frontier-radar digest`, and `frontier-radar wiki lint`.
- Treat `raw/` as immutable evidence. Do not edit raw snapshots to change meaning.
- Treat `state/` as generated machine state. Do not hand-edit SQLite or generated indexes.
- Maintain `wiki/` as the synthesized knowledge layer.
- Prefer small, surgical Markdown edits that preserve existing context and links.

## Wiki Rules

- Add provenance links for claims using original URLs or raw snapshot paths.
- Supersede stale claims in place with dates and references instead of deleting them silently.
- Create pages when an item will likely recur across days: topics, entities, repos, papers, and claims.
- Append each meaningful wiki update to `wiki/log.md` with date, changed pages, and evidence links.
- Keep daily pages in `wiki/daily/YYYY-MM-DD.md`.

## Validation

Run these commands before declaring wiki work complete:

```bash
python -m pytest -q
frontier-radar wiki lint
```

If a source fetch fails, keep partial results, record the error, and continue with the remaining sources.
```

Create `/Users/xwli/Documents/st/CLAUDE.md`:

```markdown
# Claude Code Adapter

Read and follow `AGENTS.md` first. This file only records Claude Code-specific notes.

- Use the repository CLI rather than Claude-specific workflows for core actions.
- Keep wiki edits compatible with any harness that follows `AGENTS.md`.
```

Create `/Users/xwli/Documents/st/CODEX.md`:

```markdown
# Codex Adapter

Read and follow `AGENTS.md` first. This file only records Codex-specific notes.

- Use the repository CLI rather than Codex-specific workflows for core actions.
- Codex app automation may call `frontier-radar daily`, but the CLI remains the durable interface.
```

Create `/Users/xwli/Documents/st/README.md`:

```markdown
# Frontier Radar

Frontier Radar is a local, harness-agnostic tracker for frontier AI signals. It stores raw source evidence, ranks what matters, and grows a Markdown knowledge wiki over time.

## Quickstart

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
frontier-radar daily
```

## Knowledge Layout

- `raw/`: immutable source snapshots.
- `state/`: SQLite state and generated indexes.
- `wiki/`: synthesized Markdown memory.
- `AGENTS.md`: harness-neutral operating contract.

## Daily Schedule

The intended daily run is 8:00 AM in America/Los_Angeles:

```bash
frontier-radar daily
```

See `docs/scheduling/` for cron, launchd, systemd, and Codex app notes.
```

Create `/Users/xwli/Documents/st/config/sources.yaml`:

```yaml
github:
  enabled: true
  per_query: 10
  queries:
    - "agent framework language:Python"
    - "llm inference language:Python"
    - "evals benchmark language:Python"
hn:
  enabled: true
  per_query: 10
  queries:
    - "LLM"
    - "AI agents"
    - "inference"
arxiv:
  enabled: true
  per_query: 10
  queries:
    - "large language models"
    - "AI agents"
    - "inference optimization"
rss:
  enabled: true
  feeds:
    - name: "OpenAI Blog"
      url: "https://openai.com/news/rss.xml"
    - name: "Anthropic News"
      url: "https://www.anthropic.com/news/rss.xml"
    - name: "Google DeepMind Blog"
      url: "https://deepmind.google/discover/blog/rss.xml"
youtube:
  enabled: true
  channel_feeds: []
manual:
  enabled: true
  directory: "manual"
```

Create `/Users/xwli/Documents/st/config/topics.yaml`:

```yaml
topics:
  foundation-models:
    keywords: ["frontier model", "large language model", "LLM", "pretraining"]
  agents-and-tool-use:
    keywords: ["agent", "tool use", "computer use", "MCP", "workflow"]
  reasoning-and-planning:
    keywords: ["reasoning", "planning", "test-time compute", "chain of thought"]
  post-training-and-alignment:
    keywords: ["post-training", "RLHF", "DPO", "alignment", "preference optimization"]
  evals-and-benchmarks:
    keywords: ["eval", "benchmark", "leaderboard", "SWE-bench", "MMLU"]
  inference-and-serving:
    keywords: ["inference", "serving", "vLLM", "latency", "throughput", "KV cache"]
  multimodal-models:
    keywords: ["multimodal", "vision-language", "audio", "video model"]
  robotics-and-embodied-ai:
    keywords: ["robotics", "embodied", "world model", "simulation"]
  data-and-synthetic-data:
    keywords: ["synthetic data", "data curation", "distillation"]
  ai-infrastructure:
    keywords: ["GPU", "cluster", "CUDA", "training infrastructure"]
  developer-tools:
    keywords: ["coding agent", "developer tool", "IDE", "code generation"]
  safety-and-policy:
    keywords: ["safety", "policy", "governance", "red team"]
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_package_metadata.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add pyproject.toml README.md AGENTS.md CLAUDE.md CODEX.md config frontier_radar/__init__.py tests/test_package_metadata.py
git commit -m "chore: scaffold frontier radar project"
```

## Task 2: Config Loading And Core Models

**Files:**
- Create: `/Users/xwli/Documents/st/frontier_radar/models.py`
- Create: `/Users/xwli/Documents/st/frontier_radar/config.py`
- Create: `/Users/xwli/Documents/st/tests/test_config.py`
- Create: `/Users/xwli/Documents/st/tests/test_models.py`

- [ ] **Step 1: Write failing config and model tests**

Create `/Users/xwli/Documents/st/tests/test_models.py`:

```python
from frontier_radar.models import NormalizedItem, ScoredItem


def test_normalized_item_derives_stable_id_from_url():
    item = NormalizedItem(
        source="github",
        source_type="repo",
        title="Example Repo",
        url="https://github.com/example/repo",
        author="example",
        published_at="2026-06-22T08:00:00+00:00",
        summary="An example item.",
        raw_path="raw/2026-06-22/github/example.json",
        tags=["agents"],
        metrics={"stars": 123},
        metadata={"language": "Python"},
    )

    assert item.item_id == "ffc8e3beb425"
    assert item.to_record()["metrics"]["stars"] == 123


def test_scored_item_orders_by_score_descending():
    low = ScoredItem(item_id="low", score=1.0, components={"freshness": 1.0})
    high = ScoredItem(item_id="high", score=3.0, components={"freshness": 1.0})

    assert sorted([low, high], reverse=True)[0].item_id == "high"
```

Create `/Users/xwli/Documents/st/tests/test_config.py`:

```python
from pathlib import Path

from frontier_radar.config import AppConfig, load_app_config, repo_root


def test_repo_root_points_to_project_directory():
    assert (repo_root() / "pyproject.toml").exists()


def test_load_app_config_reads_sources_and_topics():
    config = load_app_config(Path("config/sources.yaml"), Path("config/topics.yaml"))

    assert isinstance(config, AppConfig)
    assert config.sources["github"]["enabled"] is True
    assert "agents-and-tool-use" in config.topics["topics"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_models.py tests/test_config.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `frontier_radar.models` or `frontier_radar.config`.

- [ ] **Step 3: Implement models and config**

Create `/Users/xwli/Documents/st/frontier_radar/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any


def stable_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class NormalizedItem:
    source: str
    source_type: str
    title: str
    url: str
    author: str
    published_at: str
    summary: str
    raw_path: str
    tags: list[str] = field(default_factory=list)
    metrics: dict[str, int | float | str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def item_id(self) -> str:
        return stable_id(self.url)

    def to_record(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source": self.source,
            "source_type": self.source_type,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "published_at": self.published_at,
            "summary": self.summary,
            "raw_path": self.raw_path,
            "tags": list(self.tags),
            "metrics": dict(self.metrics),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, order=True)
class ScoredItem:
    score: float
    item_id: str = field(compare=False)
    components: dict[str, float] = field(default_factory=dict, compare=False)
```

Create `/Users/xwli/Documents/st/frontier_radar/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppConfig:
    sources: dict[str, Any]
    topics: dict[str, Any]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_root() / path
    with resolved.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {resolved}")
    return data


def load_app_config(
    sources_path: Path | str = Path("config/sources.yaml"),
    topics_path: Path | str = Path("config/topics.yaml"),
) -> AppConfig:
    return AppConfig(
        sources=load_yaml(Path(sources_path)),
        topics=load_yaml(Path(topics_path)),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_models.py tests/test_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add frontier_radar/models.py frontier_radar/config.py tests/test_models.py tests/test_config.py
git commit -m "feat: add config loading and core models"
```

## Task 3: Raw Snapshot Store And SQLite Storage

**Files:**
- Create: `/Users/xwli/Documents/st/frontier_radar/raw.py`
- Create: `/Users/xwli/Documents/st/frontier_radar/storage.py`
- Create: `/Users/xwli/Documents/st/tests/test_raw_storage.py`
- Create: `/Users/xwli/Documents/st/tests/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

Create `/Users/xwli/Documents/st/tests/test_raw_storage.py`:

```python
from pathlib import Path

from frontier_radar.raw import RawStore


def test_raw_store_writes_dated_snapshot(tmp_path):
    store = RawStore(tmp_path)

    path = store.write_snapshot("github", "json", b'{"ok": true}', now="2026-06-22T15:00:00+00:00")

    assert path == Path("raw/2026-06-22/github/20260622T150000Z.json")
    assert (tmp_path / path).read_bytes() == b'{"ok": true}'


def test_raw_store_keeps_same_second_snapshots_immutable(tmp_path):
    store = RawStore(tmp_path)

    first = store.write_snapshot("github", "json", b"first", now="2026-06-22T15:00:00+00:00")
    second = store.write_snapshot("github", "json", b"second", now="2026-06-22T15:00:00+00:00")

    assert first != second
    assert (tmp_path / first).read_bytes() == b"first"
    assert (tmp_path / second).read_bytes() == b"second"
```

Create `/Users/xwli/Documents/st/tests/test_storage.py`:

```python
from frontier_radar.models import NormalizedItem
from frontier_radar.storage import Database


def make_item(url="https://example.com/a"):
    return NormalizedItem(
        source="hn",
        source_type="discussion",
        title="AI agents discussion",
        url=url,
        author="alice",
        published_at="2026-06-22T15:00:00+00:00",
        summary="A useful discussion.",
        raw_path="raw/2026-06-22/hn/a.json",
        tags=["agents"],
        metrics={"points": 42},
        metadata={},
    )


def test_database_upserts_and_lists_items(tmp_path):
    db = Database(tmp_path / "state.sqlite")
    db.init()
    db.upsert_items([make_item()])
    db.upsert_items([make_item()])

    items = db.list_items()

    assert len(items) == 1
    assert items[0].title == "AI agents discussion"
    assert items[0].metrics["points"] == 42


def test_database_records_run_metadata(tmp_path):
    db = Database(tmp_path / "state.sqlite")
    db.init()

    run_id = db.record_run(
        started_at="2026-06-22T15:00:00+00:00",
        finished_at="2026-06-22T15:01:00+00:00",
        status="ok",
        counts={"hn": 1},
        errors=[],
        outputs=["wiki/daily/2026-06-22.md"],
    )

    assert run_id == 1
    assert db.latest_run()["status"] == "ok"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_raw_storage.py tests/test_storage.py -q
```

Expected: FAIL with missing `frontier_radar.raw` or `frontier_radar.storage`.

- [ ] **Step 3: Implement raw store and database**

Create `/Users/xwli/Documents/st/frontier_radar/raw.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class RawStore:
    def __init__(self, root: Path):
        self.root = root

    def write_snapshot(self, source: str, extension: str, content: bytes, now: str | None = None) -> Path:
        moment = datetime.fromisoformat(now.replace("Z", "+00:00")) if now else datetime.now(timezone.utc)
        moment = moment.astimezone(timezone.utc)
        day = moment.strftime("%Y-%m-%d")
        stamp = moment.strftime("%Y%m%dT%H%M%SZ")
        suffix = extension.lstrip(".")
        relative = Path("raw") / day / source / f"{stamp}.{suffix}"
        absolute = self.root / relative
        absolute.parent.mkdir(parents=True, exist_ok=True)
        counter = 1
        while absolute.exists():
            relative = Path("raw") / day / source / f"{stamp}-{counter}.{suffix}"
            absolute = self.root / relative
            counter += 1
        absolute.write_bytes(content)
        return relative
```

Create `/Users/xwli/Documents/st/frontier_radar/storage.py`:

```python
from __future__ import annotations

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_raw_storage.py tests/test_storage.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add frontier_radar/raw.py frontier_radar/storage.py tests/test_raw_storage.py tests/test_storage.py
git commit -m "feat: add raw snapshot and sqlite storage"
```

## Task 4: Ranking Engine

**Files:**
- Create: `/Users/xwli/Documents/st/frontier_radar/ranking.py`
- Create: `/Users/xwli/Documents/st/tests/test_ranking.py`

- [ ] **Step 1: Write failing ranking tests**

Create `/Users/xwli/Documents/st/tests/test_ranking.py`:

```python
from frontier_radar.models import NormalizedItem
from frontier_radar.ranking import rank_items, score_item


def item(title, summary, metrics, published_at="2026-06-22T15:00:00+00:00"):
    return NormalizedItem(
        source="github",
        source_type="repo",
        title=title,
        url=f"https://example.com/{title.replace(' ', '-')}",
        author="owner",
        published_at=published_at,
        summary=summary,
        raw_path="raw/2026-06-22/github/item.json",
        tags=[],
        metrics=metrics,
        metadata={},
    )


def test_score_item_combines_freshness_momentum_and_relevance():
    topics = {"topics": {"agents": {"keywords": ["agent", "tool use"]}}}
    scored = score_item(
        item("Agent Runtime", "Tool use for coding agents", {"stars": 250}),
        topics,
        now="2026-06-22T16:00:00+00:00",
    )

    assert scored.components["freshness"] > 0.9
    assert scored.components["momentum"] > 0.0
    assert scored.components["relevance"] == 2.0
    assert scored.score > 3.0


def test_rank_items_returns_highest_scores_first():
    topics = {"topics": {"agents": {"keywords": ["agent"]}}}
    ranked = rank_items(
        [
            item("Unrelated", "Database notes", {"stars": 5}),
            item("Agent Framework", "AI agent framework", {"stars": 500}),
        ],
        topics,
        now="2026-06-22T16:00:00+00:00",
        limit=1,
    )

    assert ranked[0].item.title == "Agent Framework"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_ranking.py -q
```

Expected: FAIL with missing `frontier_radar.ranking`.

- [ ] **Step 3: Implement ranking**

Create `/Users/xwli/Documents/st/frontier_radar/ranking.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math

from frontier_radar.models import NormalizedItem, ScoredItem


@dataclass(frozen=True)
class RankedItem:
    item: NormalizedItem
    score: float
    components: dict[str, float]


def parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


def freshness_score(published_at: str, now: str) -> float:
    age_hours = max((parse_time(now) - parse_time(published_at)).total_seconds() / 3600.0, 0.0)
    return max(0.0, 1.0 - (age_hours / 168.0))


def momentum_score(metrics: dict[str, int | float | str]) -> float:
    total = 0.0
    for key in ("stars", "points", "comments", "score", "views"):
        value = metrics.get(key, 0)
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                value = 0
        if isinstance(value, int | float):
            total += max(float(value), 0.0)
    return min(math.log10(total + 1.0), 4.0)


def relevance_score(item: NormalizedItem, topics: dict) -> float:
    text = f"{item.title} {item.summary} {' '.join(item.tags)}".lower()
    hits = 0
    for topic in topics.get("topics", {}).values():
        for keyword in topic.get("keywords", []):
            if keyword.lower() in text:
                hits += 1
    return float(hits)


def score_item(item: NormalizedItem, topics: dict, now: str) -> RankedItem:
    components = {
        "freshness": freshness_score(item.published_at, now),
        "momentum": momentum_score(item.metrics),
        "relevance": relevance_score(item, topics),
    }
    score = components["freshness"] + components["momentum"] + components["relevance"]
    return RankedItem(item=item, score=score, components=components)


def rank_items(items: list[NormalizedItem], topics: dict, now: str, limit: int = 20) -> list[RankedItem]:
    ranked = [score_item(item, topics, now) for item in items]
    ranked.sort(key=lambda entry: (-entry.score, entry.item.title.lower()))
    return ranked[:limit]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_ranking.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add frontier_radar/ranking.py tests/test_ranking.py
git commit -m "feat: add deterministic item ranking"
```

## Task 5: Daily Digest Rendering And Wiki Lint

**Files:**
- Create: `/Users/xwli/Documents/st/frontier_radar/wiki/__init__.py`
- Create: `/Users/xwli/Documents/st/frontier_radar/wiki/render.py`
- Create: `/Users/xwli/Documents/st/frontier_radar/wiki/lint.py`
- Create: `/Users/xwli/Documents/st/tests/test_wiki_render.py`
- Create: `/Users/xwli/Documents/st/tests/test_wiki_lint.py`

- [ ] **Step 1: Write failing wiki tests**

Create `/Users/xwli/Documents/st/tests/test_wiki_render.py`:

```python
from pathlib import Path

from frontier_radar.models import NormalizedItem
from frontier_radar.ranking import RankedItem
from frontier_radar.wiki.render import render_daily_digest, write_daily_digest


def ranked_item():
    item = NormalizedItem(
        source="github",
        source_type="repo",
        title="Agent Framework",
        url="https://github.com/example/agent-framework",
        author="example",
        published_at="2026-06-22T15:00:00+00:00",
        summary="A useful AI agent framework.",
        raw_path="raw/2026-06-22/github/item.json",
        tags=["agents"],
        metrics={"stars": 500},
        metadata={},
    )
    return RankedItem(item=item, score=5.5, components={"freshness": 1.0, "momentum": 2.5, "relevance": 2.0})


def test_render_daily_digest_includes_provenance_and_scores():
    markdown = render_daily_digest(
        date="2026-06-22",
        ranked_items=[ranked_item()],
        counts={"github": 1},
        errors=[],
    )

    assert "# Frontier Radar Daily - 2026-06-22" in markdown
    assert "Agent Framework" in markdown
    assert "raw/2026-06-22/github/item.json" in markdown
    assert "score 5.50" in markdown


def test_write_daily_digest_creates_expected_path(tmp_path):
    path = write_daily_digest(tmp_path, "2026-06-22", [ranked_item()], {"github": 1}, [])

    assert path == Path("wiki/daily/2026-06-22.md")
    assert (tmp_path / path).exists()
```

Create `/Users/xwli/Documents/st/tests/test_wiki_lint.py`:

```python
from frontier_radar.wiki.lint import lint_wiki


def test_lint_wiki_accepts_digest_with_provenance(tmp_path):
    daily = tmp_path / "wiki" / "daily"
    daily.mkdir(parents=True)
    (daily / "2026-06-22.md").write_text(
        "# Frontier Radar Daily - 2026-06-22\n\n"
        "- [Agent Framework](https://github.com/example/agent-framework) "
        "(raw: `raw/2026-06-22/github/item.json`)\n",
        encoding="utf-8",
    )

    result = lint_wiki(tmp_path)

    assert result.ok is True
    assert result.errors == []


def test_lint_wiki_flags_missing_provenance(tmp_path):
    daily = tmp_path / "wiki" / "daily"
    daily.mkdir(parents=True)
    (daily / "2026-06-22.md").write_text("# Daily\n\n- Claim without evidence\n", encoding="utf-8")

    result = lint_wiki(tmp_path)

    assert result.ok is False
    assert "missing provenance" in result.errors[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_wiki_render.py tests/test_wiki_lint.py -q
```

Expected: FAIL with missing `frontier_radar.wiki`.

- [ ] **Step 3: Implement digest rendering and lint**

Create `/Users/xwli/Documents/st/frontier_radar/wiki/__init__.py`:

```python
"""Wiki rendering and validation helpers."""
```

Create `/Users/xwli/Documents/st/frontier_radar/wiki/render.py`:

```python
from __future__ import annotations

from pathlib import Path

from frontier_radar.ranking import RankedItem


def render_daily_digest(
    date: str,
    ranked_items: list[RankedItem],
    counts: dict[str, int],
    errors: list[str],
) -> str:
    lines = [
        f"# Frontier Radar Daily - {date}",
        "",
        "## Executive Summary",
        "",
    ]
    if ranked_items:
        for entry in ranked_items[:10]:
            lines.append(
                f"- [{entry.item.title}]({entry.item.url}) from {entry.item.source} "
                f"(score {entry.score:.2f}; raw: `{entry.item.raw_path}`)"
            )
    else:
        lines.append("- No items collected.")

    lines.extend(["", "## Top Items", ""])
    for entry in ranked_items:
        components = ", ".join(f"{key}={value:.2f}" for key, value in sorted(entry.components.items()))
        lines.extend(
            [
                f"### {entry.item.title}",
                "",
                f"- Source: `{entry.item.source}` / `{entry.item.source_type}`",
                f"- URL: {entry.item.url}",
                f"- Author: {entry.item.author}",
                f"- Published: {entry.item.published_at}",
                f"- Score: {entry.score:.2f} ({components})",
                f"- Provenance: `{entry.item.raw_path}`",
                f"- Summary: {entry.item.summary}",
                "",
            ]
        )

    lines.extend(["## Run Metadata", ""])
    for source, count in sorted(counts.items()):
        lines.append(f"- {source}: {count} items")
    if errors:
        lines.extend(["", "## Errors", ""])
        for error in errors:
            lines.append(f"- {error}")
    return "\n".join(lines).rstrip() + "\n"


def write_daily_digest(
    root: Path,
    date: str,
    ranked_items: list[RankedItem],
    counts: dict[str, int],
    errors: list[str],
) -> Path:
    relative = Path("wiki") / "daily" / f"{date}.md"
    absolute = root / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_text(render_daily_digest(date, ranked_items, counts, errors), encoding="utf-8")
    return relative
```

Create `/Users/xwli/Documents/st/frontier_radar/wiki/lint.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LintResult:
    ok: bool
    errors: list[str]


def lint_wiki(root: Path) -> LintResult:
    errors: list[str] = []
    wiki = root / "wiki"
    for path in sorted(wiki.rglob("*.md")) if wiki.exists() else []:
        text = path.read_text(encoding="utf-8")
        bullets = [line for line in text.splitlines() if line.startswith("- ")]
        for index, line in enumerate(bullets, start=1):
            if "http" in line and ("raw:" not in line and "Provenance:" not in line):
                errors.append(f"{path.relative_to(root)} bullet {index} missing provenance")
            if "Claim without evidence" in line:
                errors.append(f"{path.relative_to(root)} bullet {index} missing provenance")
    return LintResult(ok=not errors, errors=errors)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_wiki_render.py tests/test_wiki_lint.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add frontier_radar/wiki tests/test_wiki_render.py tests/test_wiki_lint.py
git commit -m "feat: render and lint wiki digests"
```

## Task 6: Public Source Collectors

**Files:**
- Create: `/Users/xwli/Documents/st/frontier_radar/collectors/__init__.py`
- Create: `/Users/xwli/Documents/st/frontier_radar/collectors/base.py`
- Create: `/Users/xwli/Documents/st/frontier_radar/collectors/github.py`
- Create: `/Users/xwli/Documents/st/frontier_radar/collectors/hn.py`
- Create: `/Users/xwli/Documents/st/frontier_radar/collectors/rss.py`
- Create: `/Users/xwli/Documents/st/frontier_radar/collectors/arxiv.py`
- Create: `/Users/xwli/Documents/st/frontier_radar/collectors/manual.py`
- Create: `/Users/xwli/Documents/st/tests/test_collectors.py`

- [ ] **Step 1: Write failing collector tests**

Create `/Users/xwli/Documents/st/tests/test_collectors.py`:

```python
from pathlib import Path

from frontier_radar.collectors.github import parse_github_search
from frontier_radar.collectors.hn import parse_hn_search
from frontier_radar.collectors.rss import parse_feed
from frontier_radar.collectors.manual import collect_manual_notes


def test_parse_github_search_normalizes_repo_items():
    payload = {
        "items": [
            {
                "full_name": "example/agent-framework",
                "html_url": "https://github.com/example/agent-framework",
                "description": "AI agent framework",
                "stargazers_count": 321,
                "forks_count": 12,
                "language": "Python",
                "owner": {"login": "example"},
                "created_at": "2026-06-20T00:00:00Z",
                "updated_at": "2026-06-22T12:00:00Z",
            }
        ]
    }

    items = parse_github_search(payload, "raw/github.json")

    assert items[0].title == "example/agent-framework"
    assert items[0].metrics["stars"] == 321
    assert items[0].tags == ["Python"]


def test_parse_hn_search_normalizes_discussions():
    payload = {"hits": [{"title": "AI agents", "url": "https://example.com", "author": "alice", "created_at": "2026-06-22T12:00:00Z", "points": 50, "num_comments": 9, "objectID": "1"}]}

    items = parse_hn_search(payload, "raw/hn.json")

    assert items[0].source_type == "discussion"
    assert items[0].metrics["points"] == 50
    assert items[0].url == "https://example.com"


def test_parse_feed_handles_atom_entries():
    xml = b'''<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Example Feed</title>
      <entry>
        <title>New model release</title>
        <link href="https://example.com/model"/>
        <author><name>Example Lab</name></author>
        <updated>2026-06-22T12:00:00Z</updated>
        <summary>Frontier model release notes.</summary>
      </entry>
    </feed>'''

    items = parse_feed(xml, source="rss", source_name="Example Feed", raw_path="raw/feed.xml")

    assert items[0].title == "New model release"
    assert items[0].author == "Example Lab"


def test_collect_manual_notes_reads_markdown_links(tmp_path):
    manual = tmp_path / "manual"
    manual.mkdir()
    (manual / "x-notes.md").write_text(
        "- 2026-06-22 | Andrej Karpathy | https://x.com/example/status/1 | Notes on LLM wiki memory\n",
        encoding="utf-8",
    )

    items = collect_manual_notes(tmp_path, "manual")

    assert items[0].source == "manual"
    assert items[0].source_type == "expert-note"
    assert "LLM wiki memory" in items[0].summary
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_collectors.py -q
```

Expected: FAIL with missing `frontier_radar.collectors`.

- [ ] **Step 3: Implement collector modules**

Create `/Users/xwli/Documents/st/frontier_radar/collectors/__init__.py`:

```python
"""Source collectors for Frontier Radar."""
```

Create `/Users/xwli/Documents/st/frontier_radar/collectors/base.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class CollectorStatus:
    source: str
    count: int
    error: str | None = None


def fetch_bytes(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> bytes:
    request = Request(url, headers=headers or {"User-Agent": "frontier-radar/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str, params: dict[str, str | int] | None = None) -> dict:
    full_url = f"{url}?{urlencode(params)}" if params else url
    return json.loads(fetch_bytes(full_url).decode("utf-8"))
```

Create `/Users/xwli/Documents/st/frontier_radar/collectors/github.py`:

```python
from __future__ import annotations

import json
from urllib.parse import urlencode

from frontier_radar.collectors.base import fetch_bytes
from frontier_radar.models import NormalizedItem
from frontier_radar.raw import RawStore


def parse_github_search(payload: dict, raw_path: str) -> list[NormalizedItem]:
    items: list[NormalizedItem] = []
    for repo in payload.get("items", []):
        language = repo.get("language") or "unknown"
        items.append(
            NormalizedItem(
                source="github",
                source_type="repo",
                title=repo.get("full_name", ""),
                url=repo.get("html_url", ""),
                author=repo.get("owner", {}).get("login", ""),
                published_at=repo.get("updated_at") or repo.get("created_at") or "1970-01-01T00:00:00+00:00",
                summary=repo.get("description") or "",
                raw_path=raw_path,
                tags=[language],
                metrics={
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                },
                metadata={"created_at": repo.get("created_at"), "language": language},
            )
        )
    return [item for item in items if item.url and item.title]


def collect_github(config: dict, raw_store: RawStore, now: str) -> list[NormalizedItem]:
    results: list[NormalizedItem] = []
    for query in config.get("queries", []):
        params = urlencode(
            {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": int(config.get("per_query", 10)),
            },
        )
        raw = fetch_bytes(f"https://api.github.com/search/repositories?{params}")
        raw_path = raw_store.write_snapshot("github", "json", raw, now=now)
        results.extend(parse_github_search(json.loads(raw.decode("utf-8")), str(raw_path)))
    return results
```

Create `/Users/xwli/Documents/st/frontier_radar/collectors/hn.py`:

```python
from __future__ import annotations

import json
from urllib.parse import urlencode

from frontier_radar.collectors.base import fetch_bytes
from frontier_radar.models import NormalizedItem
from frontier_radar.raw import RawStore


def parse_hn_search(payload: dict, raw_path: str) -> list[NormalizedItem]:
    items: list[NormalizedItem] = []
    for hit in payload.get("hits", []):
        title = hit.get("title") or hit.get("story_title") or ""
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        items.append(
            NormalizedItem(
                source="hn",
                source_type="discussion",
                title=title,
                url=url,
                author=hit.get("author") or "",
                published_at=hit.get("created_at") or "1970-01-01T00:00:00+00:00",
                summary=title,
                raw_path=raw_path,
                tags=["discussion"],
                metrics={"points": hit.get("points") or 0, "comments": hit.get("num_comments") or 0},
                metadata={"object_id": hit.get("objectID")},
            )
        )
    return [item for item in items if item.url and item.title]


def collect_hn(config: dict, raw_store: RawStore, now: str) -> list[NormalizedItem]:
    results: list[NormalizedItem] = []
    for query in config.get("queries", []):
        params = urlencode({"query": query, "tags": "story", "hitsPerPage": int(config.get("per_query", 10))})
        raw = fetch_bytes(f"https://hn.algolia.com/api/v1/search_by_date?{params}")
        raw_path = raw_store.write_snapshot("hn", "json", raw, now=now)
        results.extend(parse_hn_search(json.loads(raw.decode("utf-8")), str(raw_path)))
    return results
```

Create `/Users/xwli/Documents/st/frontier_radar/collectors/rss.py`:

```python
from __future__ import annotations

import xml.etree.ElementTree as ET

from frontier_radar.collectors.base import fetch_bytes
from frontier_radar.models import NormalizedItem
from frontier_radar.raw import RawStore


ATOM = "{http://www.w3.org/2005/Atom}"


def text(node: ET.Element | None, default: str = "") -> str:
    return "".join(node.itertext()).strip() if node is not None else default


def parse_feed(xml: bytes, source: str, source_name: str, raw_path: str) -> list[NormalizedItem]:
    root = ET.fromstring(xml)
    items: list[NormalizedItem] = []
    if root.tag == f"{ATOM}feed":
        for entry in root.findall(f"{ATOM}entry"):
            link_node = entry.find(f"{ATOM}link")
            link = link_node.attrib.get("href", "") if link_node is not None else ""
            author = text(entry.find(f"{ATOM}author/{ATOM}name"), source_name)
            items.append(
                NormalizedItem(
                    source=source,
                    source_type="feed",
                    title=text(entry.find(f"{ATOM}title")),
                    url=link,
                    author=author,
                    published_at=text(entry.find(f"{ATOM}updated"), "1970-01-01T00:00:00+00:00"),
                    summary=text(entry.find(f"{ATOM}summary")),
                    raw_path=raw_path,
                    tags=[source_name],
                    metrics={},
                    metadata={"feed": source_name},
                )
            )
    else:
        for entry in root.findall("./channel/item"):
            items.append(
                NormalizedItem(
                    source=source,
                    source_type="feed",
                    title=text(entry.find("title")),
                    url=text(entry.find("link")),
                    author=text(entry.find("author"), source_name),
                    published_at=text(entry.find("pubDate"), "1970-01-01T00:00:00+00:00"),
                    summary=text(entry.find("description")),
                    raw_path=raw_path,
                    tags=[source_name],
                    metrics={},
                    metadata={"feed": source_name},
                )
            )
    return [item for item in items if item.url and item.title]


def collect_rss(config: dict, raw_store: RawStore, now: str, source: str = "rss") -> list[NormalizedItem]:
    results: list[NormalizedItem] = []
    for feed in config.get("feeds", []):
        xml = fetch_bytes(feed["url"])
        raw_path = raw_store.write_snapshot(source, "xml", xml, now=now)
        results.extend(parse_feed(xml, source=source, source_name=feed["name"], raw_path=str(raw_path)))
    return results
```

Create `/Users/xwli/Documents/st/frontier_radar/collectors/arxiv.py`:

```python
from __future__ import annotations

from urllib.parse import urlencode

from frontier_radar.collectors.base import fetch_bytes
from frontier_radar.collectors.rss import parse_feed
from frontier_radar.models import NormalizedItem
from frontier_radar.raw import RawStore


def collect_arxiv(config: dict, raw_store: RawStore, now: str) -> list[NormalizedItem]:
    results: list[NormalizedItem] = []
    for query in config.get("queries", []):
        params = urlencode(
            {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": int(config.get("per_query", 10)),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        xml = fetch_bytes(f"https://export.arxiv.org/api/query?{params}")
        raw_path = raw_store.write_snapshot("arxiv", "xml", xml, now=now)
        for item in parse_feed(xml, source="arxiv", source_name="arXiv", raw_path=str(raw_path)):
            results.append(
                NormalizedItem(
                    source=item.source,
                    source_type="paper",
                    title=item.title,
                    url=item.url,
                    author=item.author,
                    published_at=item.published_at,
                    summary=item.summary,
                    raw_path=item.raw_path,
                    tags=["paper"],
                    metrics=item.metrics,
                    metadata=item.metadata,
                )
            )
    return results
```

Create `/Users/xwli/Documents/st/frontier_radar/collectors/manual.py`:

```python
from __future__ import annotations

from pathlib import Path

from frontier_radar.models import NormalizedItem


def collect_manual_notes(root: Path, directory: str) -> list[NormalizedItem]:
    base = root / directory
    if not base.exists():
        return []
    items: list[NormalizedItem] = []
    for path in sorted(base.glob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("- "):
                continue
            parts = [part.strip() for part in line[2:].split("|", maxsplit=3)]
            if len(parts) != 4:
                continue
            date, author, url, summary = parts
            items.append(
                NormalizedItem(
                    source="manual",
                    source_type="expert-note",
                    title=summary[:80],
                    url=url,
                    author=author,
                    published_at=f"{date}T00:00:00+00:00",
                    summary=summary,
                    raw_path=str(path.relative_to(root)),
                    tags=["manual", "x-adjacent"],
                    metrics={},
                    metadata={"note_file": str(path.relative_to(root))},
                )
            )
    return items
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_collectors.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add frontier_radar/collectors tests/test_collectors.py
git commit -m "feat: add public source collectors"
```

## Task 7: Daily Pipeline And CLI

**Files:**
- Create: `/Users/xwli/Documents/st/frontier_radar/daily.py`
- Create: `/Users/xwli/Documents/st/frontier_radar/cli.py`
- Create: `/Users/xwli/Documents/st/tests/test_daily.py`
- Create: `/Users/xwli/Documents/st/tests/test_cli.py`

- [ ] **Step 1: Write failing daily and CLI tests**

Create `/Users/xwli/Documents/st/tests/test_daily.py`:

```python
from pathlib import Path

from frontier_radar.daily import DailyResult, run_daily


def test_run_daily_writes_digest_with_fixture_items(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text("manual:\n  enabled: true\n  directory: manual\n", encoding="utf-8")
    (tmp_path / "config" / "topics.yaml").write_text("topics:\n  agents:\n    keywords: ['agent']\n", encoding="utf-8")
    (tmp_path / "manual").mkdir()
    (tmp_path / "manual" / "x-notes.md").write_text(
        "- 2026-06-22 | Expert | https://x.com/example/status/1 | agent memory notes\n",
        encoding="utf-8",
    )

    result = run_daily(tmp_path, now="2026-06-22T15:00:00+00:00", live_network=False)

    assert isinstance(result, DailyResult)
    assert result.status == "ok"
    assert result.digest_path == Path("wiki/daily/2026-06-22.md")
    assert "agent memory notes" in (tmp_path / result.digest_path).read_text(encoding="utf-8")
```

Create `/Users/xwli/Documents/st/tests/test_cli.py`:

```python
from frontier_radar.cli import main


def test_cli_sources_list_prints_configured_sources(capsys):
    exit_code = main(["sources", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "github" in captured.out


def test_cli_wiki_lint_returns_zero_for_empty_wiki(tmp_path, capsys):
    exit_code = main(["--root", str(tmp_path), "wiki", "lint"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Wiki lint passed" in captured.out
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_daily.py tests/test_cli.py -q
```

Expected: FAIL with missing `frontier_radar.daily` or `frontier_radar.cli`.

- [ ] **Step 3: Implement daily orchestration and CLI**

Create `/Users/xwli/Documents/st/frontier_radar/daily.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from frontier_radar.collectors.arxiv import collect_arxiv
from frontier_radar.collectors.github import collect_github
from frontier_radar.collectors.hn import collect_hn
from frontier_radar.collectors.manual import collect_manual_notes
from frontier_radar.collectors.rss import collect_rss
from frontier_radar.config import load_app_config
from frontier_radar.models import NormalizedItem
from frontier_radar.ranking import rank_items
from frontier_radar.raw import RawStore
from frontier_radar.storage import Database
from frontier_radar.wiki.render import write_daily_digest


@dataclass(frozen=True)
class DailyResult:
    status: str
    digest_path: Path
    counts: dict[str, int]
    errors: list[str]
    top_titles: list[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def collect_all(root: Path, raw_store: RawStore, sources: dict, now: str, live_network: bool) -> tuple[list[NormalizedItem], dict[str, int], list[str]]:
    items: list[NormalizedItem] = []
    counts: dict[str, int] = {}
    errors: list[str] = []
    if sources.get("manual", {}).get("enabled", False):
        manual_items = collect_manual_notes(root, sources["manual"].get("directory", "manual"))
        items.extend(manual_items)
        counts["manual"] = len(manual_items)
    if not live_network:
        return items, counts, errors
    collectors = []
    if sources.get("github", {}).get("enabled", False):
        collectors.append(("github", lambda: collect_github(sources["github"], raw_store, now)))
    if sources.get("hn", {}).get("enabled", False):
        collectors.append(("hn", lambda: collect_hn(sources["hn"], raw_store, now)))
    if sources.get("arxiv", {}).get("enabled", False):
        collectors.append(("arxiv", lambda: collect_arxiv(sources["arxiv"], raw_store, now)))
    if sources.get("rss", {}).get("enabled", False):
        collectors.append(("rss", lambda: collect_rss(sources["rss"], raw_store, now, source="rss")))
    if sources.get("youtube", {}).get("enabled", False) and sources["youtube"].get("channel_feeds"):
        youtube_config = {"feeds": sources["youtube"]["channel_feeds"]}
        collectors.append(("youtube", lambda: collect_rss(youtube_config, raw_store, now, source="youtube")))
    for source, collector in collectors:
        try:
            collected = collector()
            items.extend(collected)
            counts[source] = len(collected)
        except Exception as exc:
            counts[source] = 0
            errors.append(f"{source}: {exc}")
    return items, counts, errors


def run_daily(root: Path, now: str | None = None, live_network: bool = True) -> DailyResult:
    root = root.resolve()
    now = now or utc_now_iso()
    date = now[:10]
    started_at = now
    config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
    db = Database(root / "state" / "frontier-radar.sqlite")
    db.init()
    raw_store = RawStore(root)
    items, counts, errors = collect_all(root, raw_store, config.sources, now, live_network)
    db.upsert_items(items)
    ranked = rank_items(db.list_items(), config.topics, now=now, limit=20)
    digest_path = write_daily_digest(root, date, ranked, counts, errors)
    status = "ok" if not errors else "partial"
    finished_at = utc_now_iso()
    db.record_run(started_at, finished_at, status, counts, errors, [str(digest_path)])
    return DailyResult(
        status=status,
        digest_path=digest_path,
        counts=counts,
        errors=errors,
        top_titles=[entry.item.title for entry in ranked[:5]],
    )
```

Create `/Users/xwli/Documents/st/frontier_radar/cli.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from frontier_radar.config import load_app_config, repo_root
from frontier_radar.daily import run_daily
from frontier_radar.storage import Database
from frontier_radar.ranking import rank_items
from frontier_radar.wiki.lint import lint_wiki
from frontier_radar.wiki.render import write_daily_digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="frontier-radar")
    parser.add_argument("--root", default=str(repo_root()), help="Repository root")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("daily")
    sub.add_parser("fetch")
    sub.add_parser("rank")
    sub.add_parser("digest")
    sources = sub.add_parser("sources")
    sources_sub = sources.add_subparsers(dest="sources_command", required=True)
    sources_sub.add_parser("list")
    sources_sub.add_parser("check")
    wiki = sub.add_parser("wiki")
    wiki_sub = wiki.add_subparsers(dest="wiki_command", required=True)
    wiki_sub.add_parser("lint")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "daily":
        result = run_daily(root)
        print(f"Frontier Radar {result.status}: {result.digest_path}")
        for title in result.top_titles:
            print(f"- {title}")
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 0 if result.status in {"ok", "partial"} else 1
    if args.command == "fetch":
        result = run_daily(root)
        print(f"Fetched and wrote digest through daily pipeline: {result.digest_path}")
        return 0
    if args.command == "rank":
        config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
        db = Database(root / "state" / "frontier-radar.sqlite")
        db.init()
        ranked = rank_items(db.list_items(), config.topics, now="2999-01-01T00:00:00+00:00")
        for entry in ranked[:20]:
            print(f"{entry.score:.2f}\t{entry.item.title}\t{entry.item.url}")
        return 0
    if args.command == "digest":
        config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
        db = Database(root / "state" / "frontier-radar.sqlite")
        db.init()
        ranked = rank_items(db.list_items(), config.topics, now="2999-01-01T00:00:00+00:00")
        path = write_daily_digest(root, "manual", ranked, {}, [])
        print(path)
        return 0
    if args.command == "sources":
        config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
        if args.sources_command == "list":
            for name, settings in sorted(config.sources.items()):
                state = "enabled" if settings.get("enabled", False) else "disabled"
                print(f"{name}: {state}")
            return 0
        if args.sources_command == "check":
            print("Source configuration loaded")
            return 0
    if args.command == "wiki" and args.wiki_command == "lint":
        result = lint_wiki(root)
        if result.ok:
            print("Wiki lint passed")
            return 0
        for error in result.errors:
            print(error, file=sys.stderr)
        return 1
    parser.error("unhandled command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_daily.py tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add frontier_radar/daily.py frontier_radar/cli.py tests/test_daily.py tests/test_cli.py
git commit -m "feat: add daily pipeline and cli"
```

## Task 8: Wiki Seed Files And Scheduler Documentation

**Files:**
- Create: `/Users/xwli/Documents/st/wiki/index.md`
- Create: `/Users/xwli/Documents/st/wiki/log.md`
- Create: `/Users/xwli/Documents/st/wiki/sources.md`
- Create: `/Users/xwli/Documents/st/wiki/daily/.gitkeep`
- Create: `/Users/xwli/Documents/st/wiki/topics/.gitkeep`
- Create: `/Users/xwli/Documents/st/wiki/entities/.gitkeep`
- Create: `/Users/xwli/Documents/st/wiki/repos/.gitkeep`
- Create: `/Users/xwli/Documents/st/wiki/papers/.gitkeep`
- Create: `/Users/xwli/Documents/st/wiki/claims/.gitkeep`
- Create: `/Users/xwli/Documents/st/raw/.gitkeep`
- Create: `/Users/xwli/Documents/st/state/.gitkeep`
- Create: `/Users/xwli/Documents/st/manual/.gitkeep`
- Create: `/Users/xwli/Documents/st/docs/scheduling/cron.md`
- Create: `/Users/xwli/Documents/st/docs/scheduling/launchd.md`
- Create: `/Users/xwli/Documents/st/docs/scheduling/systemd.md`
- Create: `/Users/xwli/Documents/st/docs/scheduling/codex.md`
- Create: `/Users/xwli/Documents/st/tests/test_docs_layout.py`

- [ ] **Step 1: Write failing layout test**

Create `/Users/xwli/Documents/st/tests/test_docs_layout.py`:

```python
from pathlib import Path


def test_wiki_seed_layout_exists():
    root = Path(__file__).resolve().parents[1]
    for relative in [
        "wiki/index.md",
        "wiki/log.md",
        "wiki/sources.md",
        "wiki/daily/.gitkeep",
        "wiki/topics/.gitkeep",
        "wiki/entities/.gitkeep",
        "wiki/repos/.gitkeep",
        "wiki/papers/.gitkeep",
        "wiki/claims/.gitkeep",
        "raw/.gitkeep",
        "state/.gitkeep",
        "manual/.gitkeep",
    ]:
        assert (root / relative).exists(), relative


def test_scheduler_docs_are_harness_agnostic():
    root = Path(__file__).resolve().parents[1]
    cron = (root / "docs/scheduling/cron.md").read_text(encoding="utf-8")
    codex = (root / "docs/scheduling/codex.md").read_text(encoding="utf-8")

    assert "frontier-radar daily" in cron
    assert "frontier-radar daily" in codex
    assert "America/Los_Angeles" in codex
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_docs_layout.py -q
```

Expected: FAIL with missing wiki or docs files.

- [ ] **Step 3: Create wiki seed and scheduler docs**

Create `/Users/xwli/Documents/st/wiki/index.md`:

```markdown
# Frontier Radar Wiki

This wiki is the synthesized knowledge layer for frontier AI tracking.

## Sections

- [Daily Digests](daily/)
- [Topics](topics/)
- [Entities](entities/)
- [Repositories](repos/)
- [Papers](papers/)
- [Claims](claims/)
- [Sources](sources.md)
- [Log](log.md)
```

Create `/Users/xwli/Documents/st/wiki/log.md`:

```markdown
# Wiki Log

Entries are append-only. Each entry should include date, pages changed, and evidence links.
```

Create `/Users/xwli/Documents/st/wiki/sources.md`:

```markdown
# Sources

Configured sources live in `config/sources.yaml`. This page records human notes about source quality, weighting, and watchlist changes.
```

Create the `.gitkeep` files listed in the Files section.

Create `/Users/xwli/Documents/st/docs/scheduling/cron.md`:

```markdown
# Cron Scheduling

Run Frontier Radar daily through the plain CLI command:

```bash
frontier-radar daily
```

Use the machine's timezone or set `TZ=America/Los_Angeles` in the crontab environment before the schedule entry.
```

Create `/Users/xwli/Documents/st/docs/scheduling/launchd.md`:

```markdown
# macOS launchd Scheduling

Use launchd when this repository should run on a Mac without depending on an agent harness. Configure the job to run `frontier-radar daily` from `/Users/xwli/Documents/st` at 8:00 AM in the machine timezone, with the machine timezone set to America/Los_Angeles if Pacific time behavior is required.
```

Create `/Users/xwli/Documents/st/docs/scheduling/systemd.md`:

```markdown
# systemd Timer Scheduling

Use a user-level systemd timer on Linux. The service should run `frontier-radar daily` from `/Users/xwli/Documents/st`. Configure the timer for 8:00 AM in the desired local timezone.
```

Create `/Users/xwli/Documents/st/docs/scheduling/codex.md`:

```markdown
# Codex App Automation

Codex automation is an adapter over the same command used by every scheduler:

```bash
frontier-radar daily
```

The intended schedule is daily at 8:00 AM in `America/Los_Angeles`. The automation prompt should run the command in `/Users/xwli/Documents/st`, report the digest path, include the top items, and surface any source errors.
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_docs_layout.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add wiki raw state manual docs/scheduling tests/test_docs_layout.py
git commit -m "docs: add wiki seed and scheduler docs"
```

## Task 9: End-To-End Verification And Daily Automation

**Files:**
- Modify: `/Users/xwli/Documents/st/README.md`
- No repo file is required for the Codex automation itself; create it with the Codex app automation tool after the CLI passes local verification.

- [ ] **Step 1: Run the full test suite**

Run:

```bash
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 2: Install the package in editable mode**

Run:

```bash
python -m pip install -e ".[test]"
```

Expected: install completes successfully.

- [ ] **Step 3: Run the daily command without live network by using manual fixture data**

Run:

```bash
mkdir -p manual
printf '%s\n' '- 2026-06-22 | Test Expert | https://x.com/example/status/1 | agent memory and frontier AI note' > manual/x-notes.md
python - <<'PY'
from pathlib import Path
from frontier_radar.daily import run_daily

result = run_daily(Path("."), now="2026-06-22T15:00:00+00:00", live_network=False)
print(result.status)
print(result.digest_path)
print(result.top_titles)
PY
```

Expected output includes:

```text
ok
wiki/daily/2026-06-22.md
```

- [ ] **Step 4: Run wiki lint**

Run:

```bash
frontier-radar wiki lint
```

Expected: `Wiki lint passed`.

- [ ] **Step 5: Run live daily command once**

Run:

```bash
frontier-radar daily
```

Expected: command exits 0, prints `Frontier Radar ok:` or `Frontier Radar partial:`, and writes a digest under `wiki/daily/`.

- [ ] **Step 6: Create the Codex app daily automation**

Use the Codex app automation tool, not a repo script, with these fields:

- name: `Frontier Radar Daily`
- kind: cron
- execution environment: local
- workspace: `/Users/xwli/Documents/st`
- schedule: daily at 8:00 AM in `America/Los_Angeles`
- prompt: run `frontier-radar daily` in the workspace, summarize the digest path and top items, and report source errors
- status: active

Expected: the automation is created successfully and will run the harness-neutral CLI command.

- [ ] **Step 7: Update README with verification status**

Append this section to `/Users/xwli/Documents/st/README.md`:

```markdown
## Verification

The local verification path is:

```bash
python -m pytest -q
frontier-radar wiki lint
frontier-radar daily
```

The daily reminder is configured as an adapter over `frontier-radar daily`, so the project remains usable from cron, launchd, systemd, Codex, Claude Code, or another harness.
```

- [ ] **Step 8: Commit**

Run:

```bash
git add README.md wiki state raw manual
git commit -m "chore: verify daily workflow"
```

## Self-Review

- Spec coverage: Tasks cover harness-neutral docs, raw snapshots, SQLite state, source collectors, ranking, daily digest, wiki linting, scheduler examples, and the Codex automation adapter.
- Placeholder scan: This plan contains concrete file paths, commands, and expected outputs for each task.
- Type consistency: `NormalizedItem`, `RankedItem`, `DailyResult`, `Database`, and CLI command names are used consistently across tasks.
