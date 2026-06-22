from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re


STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "can",
    "could",
    "for",
    "from",
    "have",
    "how",
    "into",
    "new",
    "that",
    "the",
    "this",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
}


@dataclass(frozen=True)
class ChatSource:
    path: Path
    title: str
    excerpt: str
    score: int


@dataclass(frozen=True)
class ChatResult:
    reply: str
    sources: list[ChatSource]
    inferred_level: str
    interests: list[str]
    transcript_path: Path | None
    profile_path: Path | None


def chat_once(
    root: Path,
    message: str,
    *,
    user_level: str | None = None,
    save: bool = True,
    now: str | None = None,
) -> ChatResult:
    root = Path(root).resolve()
    question = _inline_text(message)
    if not question:
        raise ValueError("chat message must not be empty")

    terms = _tokens(question)
    sources = _rank_wiki_pages(root, terms)
    inferred_level = user_level or _infer_level(question)
    interests = _infer_interests(terms, sources)
    reply = _render_reply(inferred_level, sources)

    transcript_path: Path | None = None
    profile_path: Path | None = None
    if save:
        timestamp = _timestamp(now)
        transcript_path = _write_transcript(
            root,
            timestamp,
            question,
            reply,
            inferred_level,
            interests,
            sources,
        )
        profile_path = _update_profile(
            root,
            timestamp,
            inferred_level,
            interests,
            transcript_path,
        )
        _append_log(root, timestamp, transcript_path, profile_path)

    return ChatResult(
        reply=reply,
        sources=sources,
        inferred_level=inferred_level,
        interests=interests,
        transcript_path=transcript_path,
        profile_path=profile_path,
    )


def _rank_wiki_pages(root: Path, terms: set[str], limit: int = 3) -> list[ChatSource]:
    if not terms:
        return []
    wiki = root / "wiki"
    scored: list[ChatSource] = []
    if not wiki.exists():
        return scored

    for path in sorted(wiki.rglob("*.md")):
        relative = path.relative_to(root)
        if _skip_wiki_page(relative):
            continue
        text = path.read_text(encoding="utf-8")
        title = _title_for(path, text)
        title_terms = _tokens(title)
        body_terms = _tokens(text)
        score = (len(terms & title_terms) * 4) + len(terms & body_terms)
        if score <= 0:
            continue
        scored.append(
            ChatSource(
                path=relative,
                title=title,
                excerpt=_best_excerpt(text, terms),
                score=score,
            )
        )
    return sorted(scored, key=lambda source: (-source.score, str(source.path)))[:limit]


def _skip_wiki_page(relative: Path) -> bool:
    parts = relative.parts
    return (
        "chats" in parts
        or relative.name in {"log.md", "user-profile.md"}
        or relative.name == ".gitkeep"
    )


def _render_reply(level: str, sources: list[ChatSource]) -> str:
    if not sources:
        return (
            "I do not have a strong wiki match for that yet. Try naming a topic, repo, "
            "paper, or claim from the daily radar so I can ground the answer in the wiki."
        )

    opener = {
        "beginner": "Here is a plain-language answer grounded in the wiki.",
        "expert": "Here is the wiki-grounded version.",
    }.get(level, "Here is a wiki-grounded answer.")

    first = sources[0]
    lines = [
        opener,
        "",
        first.excerpt,
        "",
        f"Source: `{first.path.as_posix()}`",
    ]
    if len(sources) > 1:
        lines.extend(["", "Related wiki pages:"])
        for source in sources[1:]:
            lines.append(f"- `{source.path.as_posix()}`")
    return "\n".join(lines)


def _write_transcript(
    root: Path,
    timestamp: datetime,
    question: str,
    reply: str,
    level: str,
    interests: list[str],
    sources: list[ChatSource],
) -> Path:
    relative = Path("wiki") / "chats" / f"{_timestamp_slug(timestamp)}.md"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Chat - {_timestamp_slug(timestamp)}",
        "",
        "## User Message",
        "",
        _blockquote(question),
        "",
        "## Response",
        "",
        reply,
        "",
        "## User Signals",
        "",
        f"- Explanation level: `{level}`",
        f"- Interests: {', '.join(interests) if interests else 'none detected'}",
        "",
        "## Sources",
        "",
    ]
    if sources:
        for source in sources:
            source_path = source.path.as_posix()
            lines.append(
                f"- `{source_path}` score {source.score}. Provenance: `{source_path}`"
            )
    else:
        lines.append("- No matching wiki page found.")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return relative


def _update_profile(
    root: Path,
    timestamp: datetime,
    level: str,
    interests: list[str],
    transcript_path: Path,
) -> Path:
    relative = Path("wiki") / "user-profile.md"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        text = path.read_text(encoding="utf-8").rstrip() + "\n\n"
    else:
        text = (
            "# User Profile\n\n"
            "This page captures interaction signals from Frontier Radar chat sessions.\n\n"
        )
    date = timestamp.date().isoformat()
    transcript = transcript_path.as_posix()
    interests_text = ", ".join(interests) if interests else "none detected"
    text += (
        f"## {date} Chat Signal\n\n"
        f"- Preferred explanation level: `{level}`. Provenance: `{transcript}`\n"
        f"- Current interests: {interests_text}. Provenance: `{transcript}`\n"
    )
    path.write_text(text, encoding="utf-8")
    return relative


def _append_log(
    root: Path,
    timestamp: datetime,
    transcript_path: Path,
    profile_path: Path,
) -> None:
    log_path = root / "wiki" / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        text = log_path.read_text(encoding="utf-8").rstrip()
    else:
        text = "# Wiki Log\n\nEntries are append-only."
    entry = (
        f"- {timestamp.date().isoformat()} chat: updated `{transcript_path.as_posix()}` "
        f"and `{profile_path.as_posix()}`; evidence `{transcript_path.as_posix()}`."
    )
    log_path.write_text(f"{text}\n{entry}\n", encoding="utf-8")


def _infer_level(message: str) -> str:
    lowered = message.casefold()
    beginner_markers = ["new to", "beginner", "plain english", "explain like", "eli5"]
    expert_markers = ["implementation", "architecture", "benchmark", "latency", "ablation"]
    if any(marker in lowered for marker in beginner_markers):
        return "beginner"
    if any(marker in lowered for marker in expert_markers):
        return "expert"
    return "intermediate"


def _infer_interests(terms: set[str], sources: list[ChatSource]) -> list[str]:
    interests: list[str] = []
    for term in sorted(terms):
        if term not in STOPWORDS:
            interests.append(term)
    for source in sources:
        for term in sorted(_tokens(source.title)):
            if term not in interests and term not in STOPWORDS:
                interests.append(term)
    return interests[:6]


def _best_excerpt(text: str, terms: set[str]) -> str:
    paragraphs = [
        _clean_markdown(paragraph)
        for paragraph in re.split(r"\n\s*\n", text)
        if _clean_markdown(paragraph)
    ]
    if not paragraphs:
        return "The matching wiki page is currently empty."
    return max(
        paragraphs,
        key=lambda paragraph: (len(_tokens(paragraph) & terms), len(paragraph)),
    )


def _title_for(path: Path, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return _inline_text(line.removeprefix("# "))
    return path.stem.replace("-", " ").title()


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", value.casefold())
        if token not in STOPWORDS
    }


def _clean_markdown(value: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#+\s*", "", text.strip())
    text = re.sub(r"^\s*-\s*", "", text)
    return _inline_text(text)


def _inline_text(value: str) -> str:
    return " ".join(str(value).split())


def _blockquote(value: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in value.splitlines())


def _timestamp(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _timestamp_slug(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
