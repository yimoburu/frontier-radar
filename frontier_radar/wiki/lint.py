from __future__ import annotations

from datetime import date as calendar_date
from dataclasses import dataclass
from pathlib import Path
import re


DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
PROVENANCE_PATH_PATTERN = re.compile(r"(?:raw:|Provenance:)\s*`([^`]+)`")


@dataclass(frozen=True)
class LintResult:
    ok: bool
    errors: list[str]


def lint_wiki(root: Path) -> LintResult:
    errors: list[str] = []
    wiki = root / "wiki"
    for path in sorted(wiki.rglob("*.md")) if wiki.exists() else []:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(root)
        if path.parent.name == "daily" and not _valid_daily_filename(path.name):
            errors.append(f"{relative} must use YYYY-MM-DD.md filename")
        if path.name == "log.md":
            errors.extend(_lint_log_entries(root, path, text))
        errors.extend(_lint_links(root, path, text))
        errors.extend(_lint_provenance_paths(root, path, text))
        bullets = [line for line in text.splitlines() if line.startswith("- ")]
        for index, line in enumerate(bullets, start=1):
            if "http" in line and not _has_provenance(line, bullets[index:]):
                errors.append(f"{relative} bullet {index} missing provenance")
            if "Claim without evidence" in line:
                errors.append(f"{relative} bullet {index} missing provenance")
    return LintResult(ok=not errors, errors=errors)


def _has_provenance(line: str, following_bullets: list[str]) -> bool:
    if "raw:" in line or "Provenance:" in line:
        return True
    return bool(following_bullets and following_bullets[0].startswith("- Provenance:"))


def _valid_daily_filename(name: str) -> bool:
    if not name.endswith(".md"):
        return False
    value = name.removesuffix(".md")
    if not DATE_PATTERN.fullmatch(value):
        return False
    try:
        calendar_date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _lint_log_entries(root: Path, path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("- ") and not re.match(r"- \d{4}-\d{2}-\d{2}\b", line):
            errors.append(f"{path.relative_to(root)} line {line_number} log entries must start with YYYY-MM-DD")
    return errors


def _lint_links(root: Path, path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for target in MARKDOWN_LINK_PATTERN.findall(text):
        link = target.split()[0].split("#", 1)[0]
        if not link or _is_external_link(link):
            continue
        resolved = (path.parent / link).resolve()
        root_resolved = root.resolve()
        if resolved != root_resolved and root_resolved not in resolved.parents:
            errors.append(f"{path.relative_to(root)} link escapes repository: {target}")
            continue
        if not resolved.exists():
            errors.append(f"{path.relative_to(root)} missing local link target: {target}")
    return errors


def _lint_provenance_paths(root: Path, path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for value in PROVENANCE_PATH_PATTERN.findall(text):
        if _is_external_link(value):
            continue
        relative_path = Path(value)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            errors.append(f"{path.relative_to(root)} unsafe provenance path: {value}")
            continue
        if _is_raw_provenance_path(relative_path):
            continue
        if not (root / relative_path).exists():
            errors.append(f"{path.relative_to(root)} missing provenance path: {value}")
    return errors


def _is_external_link(value: str) -> bool:
    lowered = value.casefold()
    return lowered.startswith(("http://", "https://", "mailto:"))


def _is_raw_provenance_path(value: Path) -> bool:
    return bool(value.parts) and value.parts[0] == "raw"
