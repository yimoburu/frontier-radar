from pathlib import Path

import pytest

from frontier_radar.raw import RawStore


def test_raw_store_writes_dated_snapshot(tmp_path):
    store = RawStore(tmp_path)

    path = store.write_snapshot("github", "json", b'{"ok": true}', now="2026-06-22T15:00:00+00:00")

    assert path == Path("raw/2026-06-22/github/20260622T150000Z.json")
    assert (tmp_path / path).read_bytes() == b'{"ok": true}'


def test_raw_store_keeps_same_second_snapshots_immutable(tmp_path):
    store = RawStore(tmp_path)

    first = store.write_snapshot("github", "json", b"first", now="2026-06-22T15:00:00+00:00")
    second = store.write_snapshot("github", "json", b"second", now="2026-06-22T15:00:00+00:00")

    assert first != second
    assert (tmp_path / first).read_bytes() == b"first"
    assert (tmp_path / second).read_bytes() == b"second"


@pytest.mark.parametrize("source", ["../escape", "/tmp/escape"])
def test_raw_store_rejects_unsafe_source_paths(tmp_path, source):
    store = RawStore(tmp_path)

    with pytest.raises(ValueError):
        store.write_snapshot(source, "json", b"unsafe", now="2026-06-22T15:00:00+00:00")


def test_raw_store_uses_exclusive_creation_when_snapshot_appears_during_write(tmp_path, monkeypatch):
    store = RawStore(tmp_path)
    base = tmp_path / "raw/2026-06-22/github/20260622T150000Z.json"
    base.parent.mkdir(parents=True)
    base.write_bytes(b"existing")
    original_exists = Path.exists

    def exists_with_race(path):
        if path == base:
            return False
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", exists_with_race)

    path = store.write_snapshot("github", "json", b"new", now="2026-06-22T15:00:00+00:00")

    assert path == Path("raw/2026-06-22/github/20260622T150000Z-1.json")
    assert base.read_bytes() == b"existing"
    assert (tmp_path / path).read_bytes() == b"new"
