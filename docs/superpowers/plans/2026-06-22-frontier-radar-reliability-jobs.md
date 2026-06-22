# Frontier Radar Reliability Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add v1.1 reliability-oriented scheduled jobs for daily, retry, enrichment, and maintenance workflows.

**Architecture:** Keep `frontier-radar daily` as the primary coordinated pipeline. Add job configuration, SQLite source-run and lock metadata, retry/enrich/health orchestration helpers, and CLI flags that override YAML defaults.

**Tech Stack:** Python 3.11, argparse, sqlite3, PyYAML, pytest.

---

## Task 1: Job Configuration

**Files:**
- Create: `config/jobs.yaml`
- Modify: `frontier_radar/config.py`
- Test: `tests/test_jobs_config.py`

- [ ] Add durable defaults for daily, retry, enrich, and maintenance jobs.
- [ ] Load defaults from `config/jobs.yaml`.
- [ ] Merge CLI overrides over YAML over built-ins.
- [ ] Record effective config for each job run.

## Task 2: SQLite Reliability State

**Files:**
- Modify: `frontier_radar/storage.py`
- Test: `tests/test_reliability_storage.py`

- [ ] Add migrated run metadata columns for `job_type` and `effective_config_json`.
- [ ] Add `source_runs` to record per-source status, counts, retry eligibility, and errors.
- [ ] Add `run_locks` with stale-lock handling.
- [ ] Add safe `VACUUM` and health helpers.

## Task 3: Daily Fast Run Reliability

**Files:**
- Modify: `frontier_radar/daily.py`
- Test: `tests/test_reliability_jobs.py`

- [ ] Add `--budget-minutes` and `--top-n` support through `run_daily`.
- [ ] Acquire a pipeline lock before writing state.
- [ ] Record source statuses and effective config.
- [ ] Return a clean locked result when an incompatible lock exists.
- [ ] Keep raw snapshot writes before ranking/digest rendering.

## Task 4: Retry Failed Job

**Files:**
- Create: `frontier_radar/jobs.py`
- Modify: `frontier_radar/daily.py`
- Test: `tests/test_reliability_jobs.py`

- [ ] Add `frontier-radar retry-failed --since today --budget-minutes 10`.
- [ ] Retry only failed, partial, or timed-out sources from the latest daily run.
- [ ] Deduplicate already-seen items.
- [ ] Record retry source status and append a retry summary to the daily digest.

## Task 5: Enrichment Job

**Files:**
- Modify: `frontier_radar/jobs.py`
- Test: `tests/test_reliability_jobs.py`

- [ ] Add `frontier-radar enrich --since 7d --budget-minutes 60 --top-n 100`.
- [ ] Update long-lived wiki pages with evidence-backed entries.
- [ ] Append new evidence without deleting or rewriting stale claims.
- [ ] Record outputs and effective config.

## Task 6: Maintenance And Health Jobs

**Files:**
- Modify: `frontier_radar/jobs.py`
- Modify: `frontier_radar/cli.py`
- Test: `tests/test_reliability_jobs.py`

- [ ] Add `frontier-radar state vacuum`.
- [ ] Add `frontier-radar health`.
- [ ] Report wiki lint, duplicate items, SQLite integrity, and stale locks.
- [ ] Clean stale locks safely after the configured threshold.

## Task 7: CLI And Docs

**Files:**
- Modify: `frontier_radar/cli.py`
- Modify: `README.md`
- Modify: `docs/scheduling/*.md`
- Test: `tests/test_cli.py`

- [ ] Add the four purpose-specific job commands and flags.
- [ ] Keep `fetch`, `rank`, and `digest` as manual helper commands, not scheduled jobs.
- [ ] Update docs with daily, retry, enrich, and maintenance examples.
