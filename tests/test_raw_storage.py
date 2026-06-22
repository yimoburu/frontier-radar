from pathlib import Path

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
