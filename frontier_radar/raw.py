from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class RawStore:
    def __init__(self, root: Path):
        self.root = root

    def write_snapshot(self, source: str, extension: str, content: bytes, now: str | None = None) -> Path:
        moment = datetime.fromisoformat(now.replace("Z", "+00:00")) if now else datetime.now(timezone.utc)
        moment = moment.astimezone(timezone.utc)
        day = moment.strftime("%Y-%m-%d")
        stamp = moment.strftime("%Y%m%dT%H%M%SZ")
        suffix = extension.lstrip(".")
        relative = Path("raw") / day / source / f"{stamp}.{suffix}"
        absolute = self.root / relative
        absolute.parent.mkdir(parents=True, exist_ok=True)

        counter = 1
        while absolute.exists():
            relative = Path("raw") / day / source / f"{stamp}-{counter}.{suffix}"
            absolute = self.root / relative
            counter += 1

        absolute.write_bytes(content)
        return relative
