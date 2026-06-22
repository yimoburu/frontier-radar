# Agent Automation

Any agent or automation harness should use the same command as every scheduler:

```bash
frontier-radar daily --budget-minutes 20 --top-n 30
```

The intended schedule is daily at 8:00 AM in `America/Los_Angeles`. The automation prompt should run the command in `/Users/xwli/Documents/st`, report the digest path, include the top items, and surface any source errors.

Recommended reliability jobs:

```bash
frontier-radar retry-failed --since today --budget-minutes 10
frontier-radar enrich --since 7d --budget-minutes 60 --top-n 100
frontier-radar wiki lint
frontier-radar state vacuum
frontier-radar health
```

Suggested cadence:

- Daily fast run: every day at 8:00 AM `America/Los_Angeles`.
- Retry/catch-up run: one to two hours after the daily run.
- Enrichment run: weekly, outside the daily digest window.
- Maintenance run: weekly, after enrichment.

Do not schedule `fetch`, `rank`, and `digest` as separate blind clock jobs. They are internal stages coordinated by the CLI through state, locks, and source status.
