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

## Verification

```bash
python -m pytest -q
frontier-radar wiki lint
frontier-radar daily
```

The daily reminder is configured as an adapter over `frontier-radar daily`, so the project remains usable from cron, launchd, systemd, Codex, Claude Code, or another harness.
