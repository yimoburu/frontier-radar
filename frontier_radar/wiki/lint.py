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
            if "http" in line and not _has_provenance(line, bullets[index:]):
                errors.append(f"{path.relative_to(root)} bullet {index} missing provenance")
            if "Claim without evidence" in line:
                errors.append(f"{path.relative_to(root)} bullet {index} missing provenance")
    return LintResult(ok=not errors, errors=errors)


def _has_provenance(line: str, following_bullets: list[str]) -> bool:
    if "raw:" in line or "Provenance:" in line:
        return True
    return bool(following_bullets and following_bullets[0].startswith("- Provenance:"))
