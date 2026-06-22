from __future__ import annotations

import argparse
from pathlib import Path
import sys
from urllib.parse import urlencode

from frontier_radar.chat import chat_once
from frontier_radar.collectors.base import fetch_bytes
from frontier_radar.config import load_app_config
from frontier_radar.jobs import run_enrich, run_health, run_retry_failed, run_state_vacuum
from frontier_radar.daily import ReviewItem, RunReview, fetch_once, run_daily, utc_now_iso
from frontier_radar.ranking import rank_items
from frontier_radar.storage import Database
from frontier_radar.web import serve as serve_web
from frontier_radar.web import stop as stop_web
from frontier_radar.wiki.lint import lint_wiki
from frontier_radar.wiki.render import write_daily_digest


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        if args.command == "daily":
            result = run_daily(root, budget_minutes=args.budget_minutes, top_n=args.top_n)
            _print_daily_result("Frontier Radar", result)
            return 0 if result.status in {"ok", "partial"} else 1

        if args.command == "retry-failed":
            result = run_retry_failed(root, since=args.since, budget_minutes=args.budget_minutes)
            _print_job_result(result)
            return 0 if result.status in {"ok", "partial"} else 1

        if args.command == "enrich":
            result = run_enrich(
                root,
                since=args.since,
                budget_minutes=args.budget_minutes,
                top_n=args.top_n,
            )
            _print_job_result(result)
            return 0 if result.status in {"ok", "partial"} else 1

        if args.command == "health":
            result = run_health(root)
            _print_health_result(result)
            return 0 if result.status == "ok" else 1

        if args.command == "state" and args.state_command == "vacuum":
            result = run_state_vacuum(root)
            print(f"state vacuum {result.status}")
            for lock in result.cleaned_locks:
                print(f"- cleaned stale lock: {lock}")
            return 0 if result.status == "ok" else 1

        if args.command == "fetch":
            result = fetch_once(root)
            _print_fetch_result(result)
            return 0 if result.status in {"ok", "partial"} else 1

        if args.command == "rank":
            config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
            db = Database(root / "state" / "frontier-radar.sqlite")
            db.init()
            ranked = rank_items(
                db.list_items(),
                config.topics,
                now=utc_now_iso(),
                limit=20,
                seen_item_ids=set(),
            )
            for entry in ranked:
                print(f"{entry.score:.2f}\t{entry.item.title}\t{entry.item.url}")
            return 0

        if args.command == "digest":
            config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
            db = Database(root / "state" / "frontier-radar.sqlite")
            db.init()
            now = utc_now_iso()
            latest_run = db.latest_run() or {"counts": {}, "errors": []}
            ranked = rank_items(
                db.list_items(),
                config.topics,
                now=now,
                limit=20,
                seen_item_ids=set(),
            )
            path = write_daily_digest(
                root,
                now[:10],
                ranked,
                latest_run["counts"],
                latest_run["errors"],
            )
            print(f"Wrote {path}")
            _print_review_summary(
                RunReview(
                    item_count=len(ranked),
                    new_items=0,
                    refreshed_items=0,
                    counts=latest_run["counts"],
                    outputs=[path],
                    why="rendered stored items ranked by freshness, momentum, relevance, novelty, source_weight",
                    top_items=[
                        ReviewItem(
                            title=entry.item.title,
                            score=entry.score,
                            components=dict(entry.components),
                        )
                        for entry in ranked[:5]
                    ],
                )
            )
            return 0

        if args.command == "chat":
            message = args.message or _read_chat_message()
            result = chat_once(
                root,
                message,
                user_level=args.level,
                save=not args.no_save,
            )
            print(result.reply)
            if result.transcript_path:
                print(f"\nSaved chat: {result.transcript_path}")
            if result.profile_path:
                print(f"Updated profile: {result.profile_path}")
            return 0

        if args.command == "serve":
            if args.stop:
                return stop_web(args.host, args.port)
            return serve_web(root, args.host, args.port)

        if args.command == "sources":
            config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
            if args.sources_command == "list":
                for name, settings in sorted(config.sources.items()):
                    state = "enabled" if settings.get("enabled", False) else "disabled"
                    print(f"{name}\t{state}")
                return 0
            if args.sources_command == "check":
                errors = _check_sources(config.sources)
                if errors:
                    for error in errors:
                        print(f"ERROR: {error}", file=sys.stderr)
                    return 1
                print("Source configuration and reachable feeds checked")
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

    daily = sub.add_parser("daily", help="run fetch, rank, and digest")
    daily.add_argument("--budget-minutes", type=int, default=None)
    daily.add_argument("--top-n", type=int, default=None)

    retry = sub.add_parser("retry-failed", help="retry failed or partial sources from the latest daily run")
    retry.add_argument("--since", default=None)
    retry.add_argument("--budget-minutes", type=int, default=None)

    enrich = sub.add_parser("enrich", help="update long-lived wiki pages from stored evidence")
    enrich.add_argument("--since", default=None)
    enrich.add_argument("--budget-minutes", type=int, default=None)
    enrich.add_argument("--top-n", type=int, default=None)

    sub.add_parser("health", help="report wiki, state, duplicate, and lock health")

    state = sub.add_parser("state", help="state maintenance")
    state_sub = state.add_subparsers(dest="state_command", required=True)
    state_sub.add_parser("vacuum", help="vacuum SQLite and clean stale locks")

    sub.add_parser("fetch", help="collect sources and update storage")
    sub.add_parser("rank", help="print ranked stored items")
    sub.add_parser("digest", help="write a digest from stored items")

    chat = sub.add_parser("chat", help="ask the wiki a question")
    chat.add_argument("-m", "--message", help="question or topic to ask about")
    chat.add_argument(
        "--level",
        choices=["beginner", "intermediate", "expert"],
        help="preferred explanation level",
    )
    chat.add_argument(
        "--no-save",
        action="store_true",
        help="do not write a chat transcript or update the user profile",
    )

    serve = sub.add_parser("serve", help="start the local web service")
    serve.add_argument("--host", default="127.0.0.1", help="interface to bind")
    serve.add_argument("--port", type=int, default=8765, help="port to listen on")
    serve.add_argument("--stop", action="store_true", help="stop the local web service")

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
    _print_review_summary(result.review)
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)


def _print_fetch_result(result) -> None:
    print(f"Frontier Radar fetch {result.status}: {result.item_count} items")
    _print_review_summary(result.review)
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)


def _print_job_result(result) -> None:
    print(f"{result.job_type} {result.status}: {result.item_count} new items")
    for source, count in sorted(result.counts.items()):
        print(f"- {source}: {count}")
    for output in result.outputs:
        print(f"- output: {output}")
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)


def _read_chat_message() -> str:
    if sys.stdin.isatty():
        print("Ask Frontier Radar: ", end="", flush=True)
        return sys.stdin.readline().strip()
    return sys.stdin.read().strip()
def _print_health_result(result) -> None:
    print(f"health {result.status}")
    for issue in result.issues:
        print(f"- {issue}")
    for lock in result.cleaned_locks:
        print(f"- cleaned stale lock: {lock}")
def _print_review_summary(review: RunReview) -> None:
    print("Review summary:")
    if review.outputs:
        print(f"- Output: {', '.join(str(path) for path in review.outputs)}")
    print(f"- Items: {review.item_count}")
    print(f"- Changed: {review.new_items} new, {review.refreshed_items} refreshed")
    if review.counts:
        counts = ", ".join(f"{source}={count}" for source, count in sorted(review.counts.items()))
        print(f"- Sources: {counts}")
    print(f"- Why: {review.why}")
    for item in review.top_items:
        components = ", ".join(
            f"{key}={value:.2f}" for key, value in sorted(item.components.items())
        )
        print(f"- Review: {item.title} (score {item.score:.2f}; {components})")


def _check_sources(sources: dict) -> list[str]:
    errors: list[str] = []
    for name, settings in sorted(sources.items()):
        if not settings.get("enabled", False):
            continue
        if name == "github":
            if not settings.get("queries"):
                errors.append(f"{name}: enabled source has no queries")
                continue
            _check_url(name, _github_check_url(settings), errors)
            continue
        if name == "hn":
            if not settings.get("queries"):
                errors.append(f"{name}: enabled source has no queries")
                continue
            _check_url(name, _hn_check_url(settings), errors)
            continue
        if name == "arxiv":
            if not settings.get("queries"):
                errors.append(f"{name}: enabled source has no queries")
                continue
            _check_url(name, _arxiv_check_url(settings), errors)
            continue
        if name == "rss":
            _check_feeds("rss", settings.get("feeds", []), errors)
            continue
        if name == "youtube":
            _check_feeds(
                "youtube",
                [{"name": url, "url": url} for url in settings.get("channel_feeds", [])],
                errors,
            )
    return errors


def _check_feeds(source: str, feeds: list[dict], errors: list[str]) -> None:
    for feed in feeds:
        name = feed.get("name") or feed.get("url") or "<unknown>"
        url = feed.get("url")
        if not url:
            errors.append(f"{source} feed {name}: missing url")
            continue
        try:
            fetch_bytes(str(url), timeout=10)
        except Exception as exc:
            errors.append(f"{source} feed {name}: {exc}")


def _check_url(source: str, url: str, errors: list[str]) -> None:
    try:
        fetch_bytes(url, timeout=10)
    except Exception as exc:
        errors.append(f"{source}: {exc}")


def _github_check_url(settings: dict) -> str:
    query = str(settings.get("queries", [""])[0])
    params = urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": 1})
    return f"https://api.github.com/search/repositories?{params}"


def _hn_check_url(settings: dict) -> str:
    query = str(settings.get("queries", [""])[0])
    params = urlencode({"query": query, "tags": "story", "hitsPerPage": 1})
    return f"https://hn.algolia.com/api/v1/search_by_date?{params}"


def _arxiv_check_url(settings: dict) -> str:
    query = str(settings.get("queries", [""])[0])
    params = urlencode(
        {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": 1,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    return f"https://export.arxiv.org/api/query?{params}"
