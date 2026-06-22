from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class CollectorStatus:
    source: str
    count: int
    error: str | None = None


def fetch_bytes(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> bytes:
    request = Request(url, headers=headers or {"User-Agent": "frontier-radar/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str, params: dict[str, str | int] | None = None) -> dict:
    full_url = f"{url}?{urlencode(params)}" if params else url
    return json.loads(fetch_bytes(full_url).decode("utf-8"))
