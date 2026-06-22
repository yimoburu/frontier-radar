from __future__ import annotations

import argparse
from pathlib import Path
import sys

from frontier_radar.config import load_app_config
from frontier_radar.daily import run_daily, utc_now_iso
from frontier_radar.ranking import rank_items
from frontier_radar.storage import Database
from frontier_radar.wiki.lint import lint_wiki
from frontier_radar.wiki.render import write_daily_digest


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        if args.command == "daily":
            result = run_daily(root)
            _print_daily_result("Frontier Radar", result)
            return 0 if result.status in {"ok", "partial"} else 1

        if args.command == "fetch":
            result = run_daily(root)
            _print_daily_result("Fetched and wrote digest", result)
            return 0 if result.status in {"ok", "partial"} else 1

        if args.command == "rank":
            config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
            db = Database(root / "state" / "frontier-radar.sqlite")
            db.init()
            ranked = rank_items(db.list_items(), config.topics, now=utc_now_iso(), limit=20)
            for entry in ranked:
                print(f"{entry.score:.2f}\t{entry.item.title}\t{entry.item.url}")
            return 0

        if args.command == "digest":
            config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
            db = Database(root / "state" / "frontier-radar.sqlite")
            db.init()
            now = utc_now_iso()
            ranked = rank_items(db.list_items(), config.topics, now=now, limit=20)
            path = write_daily_digest(root, now[:10], ranked, {}, [])
            print(f"Wrote {path}")
            return 0

        if args.command == "sources":
            config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
            if args.sources_command == "list":
                for name, settings in sorted(config.sources.items()):
                    state = "enabled" if settings.get("enabled", False) else "disabled"
                    print(f"{name}\t{state}")
                return 0
            if args.sources_command == "check":
                print("Source configuration loaded")
                return 0

        if args.command == "wiki" and args.wiki_command == "lint":
            result = lint_wiki(root)
            if result.ok:
                print("Wiki lint passed")
                return 0
            for error in result.errors:
                print(error, file=sys.stderr)
            return 1
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="frontier-radar")
    parser.add_argument("--root", default=".", help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("daily", help="run fetch, rank, and digest")
    sub.add_parser("fetch", help="collect sources through the daily pipeline")
    sub.add_parser("rank", help="print ranked stored items")
    sub.add_parser("digest", help="write a digest from stored items")

    sources = sub.add_parser("sources", help="inspect source configuration")
    sources_sub = sources.add_subparsers(dest="sources_command", required=True)
    sources_sub.add_parser("list", help="list configured sources")
    sources_sub.add_parser("check", help="validate source configuration")

    wiki = sub.add_parser("wiki", help="wiki maintenance")
    wiki_sub = wiki.add_subparsers(dest="wiki_command", required=True)
    wiki_sub.add_parser("lint", help="lint wiki markdown")

    return parser


def _print_daily_result(prefix: str, result) -> None:
    print(f"{prefix} {result.status}: {result.digest_path}")
    for title in result.top_titles[:5]:
        print(f"- {title}")
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
