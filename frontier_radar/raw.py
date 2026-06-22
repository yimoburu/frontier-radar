from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class RawStore:
    def __init__(self, root: Path):
        self.root = root

    def write_snapshot(self, source: str, extension: str, content: bytes, now: str | None = None) -> Path:
        self._validate_source(source)
        moment = datetime.fromisoformat(now.replace("Z", "+00:00")) if now else datetime.now(timezone.utc)
        moment = moment.astimezone(timezone.utc)
        day = moment.strftime("%Y-%m-%d")
        stamp = moment.strftime("%Y%m%dT%H%M%SZ")
        suffix = extension.lstrip(".")
        directory = Path("raw") / day / source
        (self.root / directory).mkdir(parents=True, exist_ok=True)

        counter = 1
        relative = directory / f"{stamp}.{suffix}"
        while True:
            absolute = self.root / relative
            try:
                with absolute.open("xb") as handle:
                    handle.write(content)
                return relative
            except FileExistsError:
                relative = directory / f"{stamp}-{counter}.{suffix}"
                counter += 1

    def _validate_source(self, source: str) -> None:
        path = Path(source)
        if (
            not source
            or source in {".", ".."}
            or path.is_absolute()
            or len(path.parts) != 1
            or "/" in source
            or "\\" in source
        ):
            raise ValueError(f"unsafe raw snapshot source: {source!r}")
