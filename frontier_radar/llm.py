from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Protocol
from urllib import request

import yaml

from frontier_radar.ranking import RankedItem


DEFAULT_API_KEY_ENV = "FRONTIER_RADAR_LLM_API_KEY"
EVIDENCE_PATH_PATTERN = re.compile(r"(?:Provenance:|raw:)\s*`([^`]+)`")


@dataclass(frozen=True)
class LLMSettings:
    enabled: bool = False
    provider: str = "openai-compatible"
    base_url: str = "https://api.openai.com/v1"
    model: str = ""
    api_key: str = ""
    timeout_seconds: int = 30
    max_items: int = 12

    @property
    def is_configured(self) -> bool:
        return self.enabled and bool(self.api_key) and bool(self.model)


@dataclass(frozen=True)
class LLMBriefResult:
    used_llm: bool
    lines: list[str] | None
    error: str = ""


class LLMClient(Protocol):
    def complete_json(self, settings: LLMSettings, messages: list[dict[str, str]]) -> dict[str, Any]:
        ...


class OpenAICompatibleClient:
    def complete_json(self, settings: LLMSettings, messages: list[dict[str, str]]) -> dict[str, Any]:
        url = settings.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=settings.timeout_seconds) as response:
            body = response.read().decode("utf-8")
        data = json.loads(body)
        content = data["choices"][0]["message"]["content"]
        return json.loads(_strip_json_fence(content))


def load_llm_settings(
    path: Path | str = Path("config/llm.yaml"),
    *,
    environ: dict[str, str] | None = None,
) -> LLMSettings:
    env = os.environ if environ is None else environ
    resolved = Path(path)
    if not resolved.exists():
        return LLMSettings()
    with resolved.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {resolved}")

    api_key_env = str(data.get("api_key_env") or DEFAULT_API_KEY_ENV)
    api_key = str(data.get("api_key") or env.get(api_key_env, ""))
    return LLMSettings(
        enabled=bool(data.get("enabled", False)),
        provider=str(data.get("provider", "openai-compatible")),
        base_url=str(data.get("base_url", "https://api.openai.com/v1")),
        model=str(data.get("model", "")),
        api_key=api_key,
        timeout_seconds=_positive_int(data.get("timeout_seconds"), 30),
        max_items=_positive_int(data.get("max_items"), 12),
    )


def synthesize_daily_brief(
    ranked_items: list[RankedItem],
    settings: LLMSettings,
    *,
    client: LLMClient | None = None,
) -> LLMBriefResult:
    if not settings.enabled:
        return LLMBriefResult(used_llm=False, lines=None)
    if not ranked_items:
        return LLMBriefResult(used_llm=False, lines=None)
    if settings.provider != "openai-compatible":
        return LLMBriefResult(
            used_llm=False,
            lines=None,
            error=f"llm synthesis: unsupported provider {settings.provider!r}",
        )
    if not settings.api_key:
        return LLMBriefResult(
            used_llm=False,
            lines=None,
            error="llm synthesis: enabled but api key is not configured",
        )
    if not settings.model:
        return LLMBriefResult(
            used_llm=False,
            lines=None,
            error="llm synthesis: enabled but model is not configured",
        )

    client = client or OpenAICompatibleClient()
    try:
        data = client.complete_json(settings, _daily_brief_messages(ranked_items, settings.max_items))
    except Exception as exc:
        return LLMBriefResult(used_llm=False, lines=None, error=f"llm synthesis: {exc}")

    fallback_raw = _inline_text(ranked_items[0].item.raw_path)
    allowed_raw_paths = {_inline_text(entry.item.raw_path) for entry in ranked_items}
    lines = _brief_lines(data, fallback_raw, allowed_raw_paths)
    if not lines:
        return LLMBriefResult(
            used_llm=False,
            lines=None,
            error="llm synthesis: response did not include a usable brief",
        )
    return LLMBriefResult(used_llm=True, lines=lines)


def _daily_brief_messages(ranked_items: list[RankedItem], max_items: int) -> list[dict[str, str]]:
    items = [
        {
            "title": entry.item.title,
            "source": entry.item.source,
            "source_type": entry.item.source_type,
            "url": entry.item.url,
            "summary": entry.item.summary,
            "raw_path": entry.item.raw_path,
            "tags": entry.item.tags,
            "score": round(entry.score, 2),
            "score_components": entry.components,
        }
        for entry in ranked_items[:max_items]
    ]
    return [
        {
            "role": "system",
            "content": (
                "You synthesize Frontier Radar daily evidence into useful wiki guidance. "
                "Return strict JSON with a key named brief containing 2 to 4 concise "
                "Markdown bullet strings. Each bullet must explain why the signal matters "
                "or what wiki page to update, and every bullet must include a raw evidence "
                "path as Provenance: `raw/or/manual/path`."
            ),
        },
        {
            "role": "user",
            "content": json.dumps({"ranked_items": items}, ensure_ascii=True),
        },
    ]


def _brief_lines(
    data: dict[str, Any],
    fallback_raw: str,
    allowed_raw_paths: set[str],
) -> list[str]:
    values = data.get("brief")
    if not isinstance(values, list):
        values = data.get("lines")
    if not isinstance(values, list):
        return []
    lines: list[str] = []
    for value in values[:4]:
        line = _normalize_brief_line(value, fallback_raw, allowed_raw_paths)
        if line:
            lines.append(line)
    return lines


def _normalize_brief_line(value: Any, fallback_raw: str, allowed_raw_paths: set[str]) -> str:
    line = _inline_text(str(value))
    if not line:
        return ""
    if not line.startswith("- "):
        line = "- " + line.lstrip("- ")
    cited_paths = EVIDENCE_PATH_PATTERN.findall(line)
    if cited_paths and all(path in allowed_raw_paths for path in cited_paths):
        return line
    line = EVIDENCE_PATH_PATTERN.sub("", line).strip()
    if "Provenance:" not in line and "raw:" not in line:
        line += f" Provenance: `{fallback_raw}`"
    return line


def _strip_json_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def _positive_int(value: Any, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, number)


def _inline_text(value: str) -> str:
    return " ".join(str(value).split())
