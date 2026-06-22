# Frontier Radar Design

## Summary

Frontier Radar is a local, harness-agnostic system for tracking frontier AI developments and compiling them into a long-lived knowledge base. It watches high-signal public sources, preserves raw evidence, ranks what changed, and maintains a Markdown wiki that compounds over time.

The project uses the LLM Wiki pattern described by Andrej Karpathy at <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f> as an architectural idea, not as the product name. The code and knowledge base must work with Codex, Claude Code, OpenCode, Gemini CLI, Cursor, or future agent harnesses because the durable interface is the filesystem: Markdown files, JSON/JSONL snapshots, SQLite state, and plain CLI commands.

## Goals

- Track state-of-the-art AI sources without requiring paid or fragile credentials in v1.
- Surface the most important daily changes across repositories, papers, videos, discussions, and curated feeds.
- Preserve immutable raw source snapshots so future agents can re-read evidence instead of trusting summaries.
- Maintain a Karpathy-style LLM Wiki: a synthesized Markdown knowledge layer with links, provenance, stale-claim handling, and change logs.
- Support multiple agent harnesses through shared contracts and thin adapters.
- Provide a daily 8:00 AM Pacific Time workflow that can run from standard schedulers or agent automation.

## Non-Goals

- Direct X API integration in v1. X tracking is represented through manual notes, curated mirrors, RSS-compatible bridges, or later credentialed adapters.
- A hosted multi-user web application.
- A full RAG/vector database stack. The primary memory is the compiled wiki; search indexes are helper artifacts.
- Autonomous publishing or outbound posting.
- Secret-dependent integrations as required setup.

## Source Coverage

V1 sources should prioritize no-credential public feeds:

- GitHub trending and search pages for emerging repositories.
- GitHub repository metadata where unauthenticated API limits are sufficient.
- arXiv search or RSS for AI papers.
- Hacker News Algolia search for discussion signals.
- YouTube RSS feeds for selected AI channels and search-compatible feeds where available.
- Curated RSS/blog sources for labs, researchers, libraries, and infrastructure teams.
- Manual watchlist notes for X posts or expert claims supplied by the user.

Each source adapter outputs a common normalized item with source name, URL, title, author or owner, timestamp, raw payload path, tags, summary candidate, and source-specific metrics such as stars, comments, score, views, or paper categories.

## Knowledge Architecture

The repository has three durable layers:

1. `raw/`: immutable source snapshots. Files are append-only except for mechanical cleanup that never changes meaning. Each fetch writes dated JSON, JSONL, HTML, XML, or text artifacts.
2. `state/`: machine state. SQLite stores normalized items, seen URLs, rankings, and run metadata. Generated indexes can live here.
3. `wiki/`: synthesized Markdown. Agents update this layer after reading raw evidence and existing wiki pages.

The wiki should use stable pages rather than daily-only summaries:

- `wiki/index.md`: navigation and current map of the knowledge base.
- `wiki/log.md`: append-only human-readable change log.
- `wiki/daily/YYYY-MM-DD.md`: daily digest and decisions.
- `wiki/topics/*.md`: concepts such as inference scaling, agent frameworks, evals, post-training, synthetic data, and hardware.
- `wiki/entities/*.md`: people, labs, companies, and projects.
- `wiki/repos/*.md`: important GitHub repositories.
- `wiki/papers/*.md`: important papers.
- `wiki/claims/*.md`: notable claims, predictions, benchmark results, and contradictions.
- `wiki/sources.md`: configured feeds and watchlists.

Wiki pages must include provenance links back to raw snapshots or original URLs. Claims that become stale should be superseded in place with dates and links, not silently deleted.

## Harness-Agnostic Contract

The project should not depend on Codex-specific instructions. The shared contract is:

- `AGENTS.md`: canonical instructions for any LLM agent operating the wiki.
- `CLAUDE.md`: Claude Code adapter that points to `AGENTS.md` and adds only Claude-specific command notes.
- `CODEX.md`: Codex adapter that points to `AGENTS.md` and adds only Codex-specific command notes.
- Future adapters such as `GEMINI.md`, `OPENCODE.md`, or `CURSOR.md` can be added without changing the core project.

`AGENTS.md` must define:

- How to ingest new raw sources.
- How to update wiki pages with surgical Markdown edits.
- How to create new pages and links.
- How to preserve provenance.
- How to handle contradictions and stale claims.
- How to update `wiki/log.md`.
- How to run validation commands.
- Which generated files should not be manually edited.

The CLI, tests, config files, and wiki schema must remain usable when no agent harness is present.

## CLI Design

The main CLI command is `frontier-radar`.

Core commands:

- `frontier-radar fetch`: collect raw source snapshots and normalize items.
- `frontier-radar rank`: score collected items for novelty, relevance, and momentum.
- `frontier-radar digest`: write a daily Markdown digest from ranked items.
- `frontier-radar daily`: run fetch, rank, digest, and print a concise terminal summary.
- `frontier-radar sources list`: show configured sources.
- `frontier-radar sources check`: verify source configuration and network reachability.
- `frontier-radar wiki lint`: validate wiki links, frontmatter, provenance markers, and log format.

The CLI should be deterministic where possible. Network collectors may change results, but ranking and rendering should be stable for the same stored inputs.

## Configuration

Configuration lives in `config/sources.yaml` and `config/topics.yaml`.

`sources.yaml` includes enabled sources, query terms, feed URLs, GitHub languages/topics, YouTube channel IDs, and curated blogs.

`topics.yaml` defines topic taxonomy and ranking keywords. V1 should include topics for:

- foundation models
- agents and tool use
- reasoning and planning
- post-training and alignment
- evals and benchmarks
- inference and serving
- multimodal models
- robotics and embodied AI
- data and synthetic data
- AI infrastructure
- developer tools
- safety and policy

No secrets are required in v1. Future credentialed adapters should read environment variables and document them separately.

## Ranking

The ranking system should combine:

- Freshness: newer items receive a boost.
- Momentum: stars, HN points, comments, or other source metrics.
- Relevance: match against configured topics and AI frontier keywords.
- Novelty: unseen URLs, new repos, or materially changed metadata.
- Source weight: curated sources can be weighted higher than broad searches.

Each ranked item should store score components so the daily digest can explain why it matters.

## Daily Digest

The daily digest page should include:

- Executive summary: 5-10 bullets.
- Top repositories.
- Top papers.
- Top discussions.
- Top videos or talks.
- Emerging topics.
- Claims to revisit.
- Suggested wiki pages to update.
- Raw run metadata and source counts.

The terminal summary printed by `frontier-radar daily` should be short enough for an automation notification. It should include the digest path, top items, and any errors.

## Scheduling

The project provides portable scheduler examples:

- cron for Unix-like systems.
- launchd for macOS.
- systemd timers for Linux.
- agent automation as an optional adapter.
- harness-specific adapter notes that delegate to the shared contract.

The requested daily schedule is 8:00 AM in `America/Los_Angeles`, preserving daylight saving behavior. The scheduled action should call the plain CLI command rather than a harness-specific workflow:

```bash
frontier-radar daily
```

Harness adapters may wrap this command, but they must not be the only way to run it.

## Error Handling

Collectors should fail independently. A broken YouTube feed should not prevent GitHub or arXiv collection.

Every run should record:

- start and end time
- source status
- item counts
- warning and error messages
- output paths

The daily digest should include partial results and a small error section when sources fail.

## Testing

Use pytest for:

- source normalization
- ranking score components
- digest rendering
- wiki linting
- config loading
- collector parsing with mocked or fixture responses
- daily pipeline behavior when one source fails

Network tests should not be required for the default test suite. Live source checks belong behind explicit commands.

## Initial File Layout

```text
.
├── AGENTS.md
├── CLAUDE.md
├── CODEX.md
├── README.md
├── config/
│   ├── sources.yaml
│   └── topics.yaml
├── docs/
│   └── superpowers/
│       └── specs/
├── frontier_radar/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── daily.py
│   ├── ranking.py
│   ├── storage.py
│   ├── collectors/
│   └── wiki/
├── raw/
│   └── .gitkeep
├── state/
│   └── .gitkeep
├── tests/
└── wiki/
    ├── index.md
    ├── log.md
    ├── sources.md
    ├── daily/
    ├── topics/
    ├── entities/
    ├── repos/
    ├── papers/
    └── claims/
```

## Implementation Phases

Phase 1 creates the project skeleton, configs, harness-neutral docs, SQLite schema, and wiki directories.

Phase 2 implements deterministic normalization, storage, ranking, and digest rendering with fixture-based tests.

Phase 3 adds public collectors for GitHub, arXiv, Hacker News, YouTube RSS, curated RSS, and manual notes.

Phase 4 adds wiki linting, scheduler examples, and the optional Codex daily automation.

## V1 Decisions

- Use `frontier-radar` as the project name for the first implementation.
- X support remains manual or RSS-bridge based in v1 because direct integration conflicts with the no-credential MVP constraint.
- Favor a reliable CLI and wiki over a web UI.
