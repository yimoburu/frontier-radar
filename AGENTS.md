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
