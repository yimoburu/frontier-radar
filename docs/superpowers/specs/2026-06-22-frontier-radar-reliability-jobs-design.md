# Frontier Radar Reliability Jobs Design

## Summary

This document captures a future v1.1 reliability improvement for Frontier Radar after the first version is complete. The goal is to make the scheduled system more dependable by adding purpose-specific jobs around the main daily pipeline:

- daily fast run
- retry and catch-up run
- weekly deep enrichment run
- weekly maintenance and health run

The key design rule is to split scheduled work by purpose, not by internal pipeline step. The system should not schedule `fetch`, `rank`, and `digest` as separate clock-based jobs. Those steps depend on each other and should remain coordinated by the CLI through SQLite state, locks, checkpoints, and source status.

## Motivation

The v1 daily command is expected to collect source data, save raw evidence, normalize items into SQLite, rank important changes, and write wiki output. A single daily command is the right primary interface, but real-world sources can be slow, flaky, unavailable, or unexpectedly large.

Reliability should come from bounded runs, independent source handling, resumable state, and targeted follow-up jobs. If one source times out, the daily run should still produce a useful partial digest. If a slow source recovers later, a retry job should catch it up. If deeper analysis takes too long for the daily window, a weekly enrichment job should handle it separately.

## Design Principles

- Keep `frontier-radar daily` as the primary daily pipeline.
- Do not use blind clock choreography for `fetch`, `rank`, and `digest`.
- Make every scheduled job idempotent.
- Save raw evidence as soon as it is fetched.
- Record checkpoints and source status in SQLite.
- Prefer partial useful output over all-or-nothing failure.
- Use separate jobs for recovery, enrichment, and maintenance.
- Make each job safe to run twice, safe to skip, and safe to resume.
- Keep ordinary tuning in config files, not Python code.

## Scheduled Job Types

### Daily Fast Run

Command:

```bash
frontier-radar daily --budget-minutes 20 --top-n 30
```

Purpose:

Run every day at 8:00 AM America/Los_Angeles. This is the main workflow. It fetches new source data, saves raw snapshots immediately, normalizes items into SQLite, ranks new or changed items, deep-processes only the top ranked items, and writes `wiki/daily/YYYY-MM-DD.md`.

Expected behavior:

- Runs within a configurable time budget.
- Handles each source independently.
- Records per-source status as success, partial, skipped, failed, or timeout.
- Produces a partial digest when at least one source succeeds or stored ranked data is available.
- Records warnings and errors in SQLite and in the digest.
- Prints a concise terminal summary for Codex Automation Triage.
- Exits cleanly if another incompatible run is active.

### Retry And Catch-Up Run

Command:

```bash
frontier-radar retry-failed --since today --budget-minutes 10
```

Purpose:

Run one to two hours after the daily fast run. It retries only sources that failed, timed out, or returned partial results in the most recent daily run.

Expected behavior:

- Does not re-run sources that already succeeded.
- Does not duplicate already-seen items.
- Writes raw snapshots immediately when retry fetches succeed.
- Updates source run status in SQLite.
- Optionally updates or appends to the same daily digest with recovered items.
- Reports recovered sources and still-failing sources.

### Weekly Deep Enrichment Run

Command:

```bash
frontier-radar enrich --since 7d --budget-minutes 60 --top-n 100
```

Purpose:

Run weekly. This job handles slower work that should not block the daily digest, such as deeper paper reading, repository README analysis, claim extraction, topic-page updates, entity-page updates, and wiki cross-linking.

Expected behavior:

- Uses already-collected raw snapshots and SQLite state where possible.
- Fetches missing details only when needed and within budget.
- Updates long-lived wiki pages such as `wiki/topics/*.md`, `wiki/entities/*.md`, `wiki/repos/*.md`, `wiki/papers/*.md`, and `wiki/claims/*.md`.
- Requires provenance links for added claims.
- Writes a concise enrichment summary.
- Does not silently remove old claims. Stale claims should be superseded with dates and evidence.

### Weekly Maintenance And Health Run

Commands:

```bash
frontier-radar wiki lint
frontier-radar state vacuum
frontier-radar health
```

Purpose:

Run weekly. This job checks wiki consistency, broken links, missing provenance, stale claims, duplicate items, SQLite health, old locks, and storage growth.

Expected behavior:

- Reports broken links, missing provenance, duplicate items, stale locks, and state health issues.
- Performs safe mechanical cleanup such as SQLite vacuum or stale lock cleanup when configured.
- Does not delete meaningful raw evidence.
- Does not rewrite wiki content unless the operation is clearly mechanical and safe.
- Produces a concise health report for Codex Automation Triage.

## Configuration

Operational job defaults should live in a durable YAML file, likely `config/daily.yaml` or `config/jobs.yaml`. CLI flags should override YAML values for one-off runs.

Suggested structure:

```yaml
daily:
  budget_minutes: 20
  top_n: 30
  max_deep_reads: 15
  partial_digest: true
  prevent_overlapping_runs: true
  stale_run_after_minutes: 60
  terminal_summary_items: 5

retry_failed:
  enabled: true
  budget_minutes: 10
  retry_window: today
  max_attempts_per_source: 2
  update_daily_digest: true

enrich:
  enabled: true
  budget_minutes: 60
  since: 7d
  top_n: 100
  update_topic_pages: true
  update_entity_pages: true
  update_claim_pages: true
  require_provenance_links: true

maintenance:
  enabled: true
  lint_wiki: true
  check_provenance: true
  check_broken_links: true
  check_duplicate_items: true
  vacuum_state: true
  stale_lock_after_minutes: 120
```

Configuration priority should be:

```text
CLI flags > config/*.yaml > built-in defaults
```

SQLite should record the effective configuration used for each run, but SQLite should not be the normal place for users to configure behavior manually.

## Codex Automation Schedule

Schedules should be configured in Codex App Automation, not in project YAML.

Recommended automations:

- Daily fast run: every day at 8:00 AM America/Los_Angeles.
- Retry and catch-up run: every day around 10:00 AM America/Los_Angeles.
- Weekly enrichment run: Saturday morning.
- Weekly maintenance and health run: Sunday morning.

Each automation should run in the project workspace. For this local knowledge base, local execution is usually preferable to an isolated worktree because `raw/`, `state/`, and `wiki/` are intended to accumulate in the main checkout.

Suggested automation prompt for the daily fast run:

```text
Run `frontier-radar daily --budget-minutes 20 --top-n 30` for the Frontier Radar project. Report the digest path, top items, source counts, and any warnings or errors. If the command is unavailable or fails, report the failure clearly with the important stderr/stdout details and do not attempt unrelated refactors.
```

Suggested automation prompt for the retry run:

```text
Run `frontier-radar retry-failed --since today --budget-minutes 10` for the Frontier Radar project. Report which sources were retried, which recovered, which still failed, and whether the daily digest was updated.
```

Suggested automation prompt for the enrichment run:

```text
Run `frontier-radar enrich --since 7d --budget-minutes 60 --top-n 100` for the Frontier Radar project. Report updated wiki pages, added claims, provenance coverage, and any warnings or errors.
```

Suggested automation prompt for the maintenance run:

```text
Run `frontier-radar wiki lint`, `frontier-radar state vacuum`, and `frontier-radar health` for the Frontier Radar project. Report broken links, missing provenance, duplicate items, SQLite health, stale locks, cleanup performed, and any remaining action items.
```

## State And Locking Requirements

The implementation should inspect the v1 storage architecture before choosing exact table names. Conceptually, SQLite should support:

- job run records
- source run records
- source status and retry eligibility
- warnings and errors
- effective config snapshots
- run locks
- stale lock detection
- seen item tracking

Every job should acquire an appropriate lock before doing work. Incompatible jobs should not overlap. For example, a daily run and retry run should not write the same run state at the same time. A read-only health check may be allowed concurrently if the implementation can guarantee safety.

If a lock is stale, the system should report it clearly and clean it only when the configured stale-lock threshold has passed.

## Output Requirements

Daily digest output should include:

- digest date
- run status
- source counts
- top items
- warnings and errors
- retry eligibility, when relevant
- links to raw evidence or original sources

Retry output should include:

- sources retried
- recovered source counts
- still-failing sources
- new or updated digest path
- warnings and errors

Enrichment output should include:

- updated wiki pages
- new claims or superseded claims
- provenance coverage
- unresolved items needing review

Maintenance output should include:

- wiki lint status
- broken links
- missing provenance
- duplicate candidates
- SQLite health
- stale locks
- cleanup performed

## Testing Requirements

The implementation should add deterministic pytest coverage without requiring live network access.

Required test cases:

- Daily run records partial success when one source fails.
- Daily run saves raw snapshots before ranking or digest rendering.
- Daily run exits cleanly when an incompatible lock exists.
- Retry run retries only failed, partial, or timed-out sources.
- Retry run does not duplicate already-seen items.
- Retry run updates source status and summary output.
- Enrichment updates long-lived wiki pages with provenance.
- Enrichment does not silently delete stale claims.
- Maintenance detects broken wiki links.
- Maintenance detects missing provenance.
- Maintenance handles stale locks safely.
- CLI flags override YAML defaults.
- SQLite records effective config for a run.

## Acceptance Criteria

- The system has four clear scheduled job types: daily, retry, enrich, and maintenance.
- The daily run remains the primary pipeline.
- Internal `fetch`, `rank`, and `digest` stages are not scheduled as separate blind clock jobs.
- Retry improves reliability without duplicating work.
- Enrichment handles slow work outside the daily budget.
- Maintenance catches wiki and state drift.
- All jobs are idempotent and checkpointed.
- Failed jobs leave useful state behind.
- Codex Automation outputs are concise and actionable.
- No job corrupts `raw/`, `state/`, or `wiki/` if interrupted.

## Future Implementation Note

After v1 is complete, this spec should be converted into an implementation plan under `docs/superpowers/plans/`. That future plan should inspect the actual v1 codebase first and name exact files, functions, schema migrations, tests, and commits. This spec should remain the stable product and reliability request.
