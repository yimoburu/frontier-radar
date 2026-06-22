# Frontier Radar

Frontier Radar is a local, harness-agnostic tracker for frontier AI signals. It stores raw source evidence, ranks what matters, and grows a Markdown knowledge wiki over time.

## Quickstart

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
frontier-radar daily
```

Ask the wiki a question in a one-shot chat:

```bash
frontier-radar chat --message "I'm new to this. What are AI agents?"
```

The chat command answers from matching wiki pages, records a transcript under `wiki/chats/`,
and updates `wiki/user-profile.md` with explanation-level and interest signals so future
wiki work can speak closer to the user's current context.

Start a local web control panel:

```bash
frontier-radar serve
```

Then open `http://127.0.0.1:8765/` to run daily, fetch, rank, digest, wiki lint, health, and chat actions from the browser.
Use the browser's Stop Server button, press `Ctrl-C` in the terminal, or run `frontier-radar serve --stop` from another terminal to stop it.

## Knowledge Layout

- `raw/`: immutable source snapshots.
- `state/`: SQLite state and generated indexes.
- `wiki/`: synthesized Markdown memory.
- `AGENTS.md`: harness-neutral operating contract.

## Daily Schedule

The intended daily run is 8:00 AM in America/Los_Angeles:

```bash
frontier-radar daily --budget-minutes 20 --top-n 30
```

See `docs/scheduling/` for cron, launchd, systemd, and agent automation notes.

Reliability jobs:

```bash
frontier-radar retry-failed --since today --budget-minutes 10
frontier-radar enrich --since 7d --budget-minutes 60 --top-n 100
frontier-radar state vacuum
frontier-radar health
```

## Verification

```bash
python -m pytest -q
frontier-radar wiki lint
frontier-radar daily
```

Daily agent automation is only an adapter over `frontier-radar daily`, so the project remains usable from cron, launchd, systemd, or any harness that can run the CLI.
