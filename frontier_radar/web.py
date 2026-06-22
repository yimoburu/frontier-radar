from __future__ import annotations

from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from frontier_radar.chat import chat_once
from frontier_radar.config import load_app_config
from frontier_radar.daily import fetch_once, run_daily, utc_now_iso
from frontier_radar.jobs import run_health
from frontier_radar.ranking import rank_items
from frontier_radar.storage import Database
from frontier_radar.wiki.lint import lint_wiki
from frontier_radar.wiki.render import write_daily_digest


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class FrontierRadarServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], root: Path):
        self.root = Path(root).resolve()
        super().__init__(server_address, FrontierRadarHandler)


class FrontierRadarHandler(BaseHTTPRequestHandler):
    server: FrontierRadarServer

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/":
            self._send_html(_render_dashboard(self.server.root))
            return
        if route == "/api/status":
            self._send_json(_status_payload(self.server.root))
            return
        if route == "/api/actions/rank":
            self._run_json(lambda: _rank_payload(self.server.root))
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        params = self._read_params()
        if route.startswith("/api/actions/"):
            action = route.removeprefix("/api/actions/")
            self._run_json(lambda: _action_payload(self.server.root, action, params))
            return
        if route == "/api/chat":
            self._run_json(lambda: _chat_payload(self.server.root, params))
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        return

    def _run_json(self, action) -> None:
        try:
            self._send_json(action())
        except ValueError as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json(
                {"status": "error", "error": str(exc)},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def _read_params(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length)
        if not body:
            return {}
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            data = json.loads(body.decode("utf-8"))
            return {str(key): str(value) for key, value in data.items() if value is not None}
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}

    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, data: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def create_server(
    root: Path,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> FrontierRadarServer:
    return FrontierRadarServer((host, port), root)


def serve(root: Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> int:
    server = create_server(root, host=host, port=port)
    address = f"http://{server.server_name}:{server.server_port}/"
    print(f"Frontier Radar web service listening on {address}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nFrontier Radar web service stopped")
    finally:
        server.server_close()
    return 0


def _action_payload(root: Path, action: str, params: dict[str, str]) -> dict:
    if action == "daily":
        result = run_daily(
            root,
            budget_minutes=_optional_int(params, "budget_minutes"),
            top_n=_optional_int(params, "top_n"),
        )
        return _daily_payload(result)
    if action == "fetch":
        return _fetch_payload(fetch_once(root))
    if action == "rank":
        return _rank_payload(root, limit=_optional_int(params, "limit") or 20)
    if action == "digest":
        return _digest_payload(root)
    if action == "wiki-lint":
        result = lint_wiki(root)
        return {
            "status": "ok" if result.ok else "error",
            "errors": result.errors,
        }
    if action == "health":
        result = run_health(root)
        return {
            "status": result.status,
            "issues": result.issues,
            "cleaned_locks": result.cleaned_locks,
        }
    raise ValueError(f"unknown action: {action}")


def _chat_payload(root: Path, params: dict[str, str]) -> dict:
    message = params.get("message", "").strip()
    level = params.get("level") or None
    save = params.get("save", "true").casefold() != "false"
    result = chat_once(root, message, user_level=level, save=save)
    return {
        "status": "ok",
        "reply": result.reply,
        "inferred_level": result.inferred_level,
        "interests": result.interests,
        "sources": [
            {
                "path": source.path.as_posix(),
                "title": source.title,
                "excerpt": source.excerpt,
                "score": source.score,
            }
            for source in result.sources
        ],
        "transcript_path": _path_or_none(result.transcript_path),
        "profile_path": _path_or_none(result.profile_path),
    }


def _rank_payload(root: Path, limit: int = 20) -> dict:
    config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
    db = Database(root / "state" / "frontier-radar.sqlite")
    db.init()
    ranked = rank_items(
        db.list_items(),
        config.topics,
        now=utc_now_iso(),
        limit=limit,
        seen_item_ids=set(),
    )
    return {
        "status": "ok",
        "items": [
            {
                "score": entry.score,
                "title": entry.item.title,
                "url": entry.item.url,
                "components": dict(entry.components),
            }
            for entry in ranked
        ],
    }


def _digest_payload(root: Path) -> dict:
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
    return {
        "status": "ok",
        "digest_path": path.as_posix(),
        "item_count": len(ranked),
        "top_items": [
            {
                "title": entry.item.title,
                "score": entry.score,
                "components": dict(entry.components),
            }
            for entry in ranked[:5]
        ],
    }


def _status_payload(root: Path) -> dict:
    db = Database(root / "state" / "frontier-radar.sqlite")
    db.init()
    latest_run = db.latest_run()
    return {
        "status": "ok",
        "root": root.as_posix(),
        "latest_run": latest_run or None,
    }


def _daily_payload(result) -> dict:
    return {
        "status": result.status,
        "digest_path": _path_or_none(result.digest_path),
        "counts": result.counts,
        "errors": result.errors,
        "top_titles": result.top_titles,
        "review": _review_payload(result.review),
    }


def _fetch_payload(result) -> dict:
    return {
        "status": result.status,
        "counts": result.counts,
        "errors": result.errors,
        "item_count": result.item_count,
        "review": _review_payload(result.review),
    }


def _review_payload(review) -> dict:
    return {
        "item_count": review.item_count,
        "new_items": review.new_items,
        "refreshed_items": review.refreshed_items,
        "counts": review.counts,
        "outputs": [_path_or_none(path) for path in review.outputs],
        "why": review.why,
        "top_items": [
            {
                "title": item.title,
                "score": item.score,
                "components": item.components,
            }
            for item in review.top_items
        ],
    }


def _optional_int(params: dict[str, str], key: str) -> int | None:
    value = params.get(key, "").strip()
    if not value:
        return None
    return int(value)


def _path_or_none(path) -> str | None:
    if path is None:
        return None
    return Path(path).as_posix()


def _render_dashboard(root: Path) -> str:
    root_text = escape(root.as_posix())
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Frontier Radar</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f6f7f9;
      color: #20242c;
    }}
    body {{ margin: 0; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 32px 20px 48px; }}
    header {{ margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 2rem; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 1.05rem; letter-spacing: 0; }}
    p {{ margin: 0; color: #5d6470; }}
    section {{ margin-top: 18px; padding: 18px; background: #fff; border: 1px solid #dfe3ea; border-radius: 8px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }}
    form {{ display: grid; gap: 10px; }}
    label {{ display: grid; gap: 5px; font-size: .9rem; color: #4a515c; }}
    input, select, textarea {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid #c8ced8;
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
      background: #fff;
      color: #20242c;
    }}
    textarea {{ min-height: 92px; resize: vertical; }}
    button {{
      border: 0;
      border-radius: 6px;
      padding: 10px 12px;
      font: inherit;
      font-weight: 650;
      background: #136f63;
      color: #fff;
      cursor: pointer;
    }}
    button.secondary {{ background: #2f566f; }}
    pre {{
      min-height: 180px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      padding: 14px;
      border-radius: 8px;
      background: #161a22;
      color: #e8edf6;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{ background: #11151b; color: #edf0f5; }}
      p {{ color: #aab2c0; }}
      section {{ background: #1b2029; border-color: #303846; }}
      label {{ color: #c5ccd8; }}
      input, select, textarea {{ background: #11151b; color: #edf0f5; border-color: #485163; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Frontier Radar</h1>
      <p>{root_text}</p>
    </header>
    <section>
      <h2>Pipeline</h2>
      <div class="grid">
        <form data-api="/api/actions/daily">
          <label>Budget minutes <input name="budget_minutes" inputmode="numeric" placeholder="20"></label>
          <label>Top items <input name="top_n" inputmode="numeric" placeholder="30"></label>
          <button type="submit">Run Daily</button>
        </form>
        <form data-api="/api/actions/fetch">
          <button type="submit" class="secondary">Fetch Sources</button>
        </form>
        <form data-api="/api/actions/rank">
          <label>Limit <input name="limit" inputmode="numeric" placeholder="20"></label>
          <button type="submit" class="secondary">Rank Items</button>
        </form>
        <form data-api="/api/actions/digest">
          <button type="submit" class="secondary">Write Digest</button>
        </form>
        <form data-api="/api/actions/wiki-lint">
          <button type="submit" class="secondary">Lint Wiki</button>
        </form>
        <form data-api="/api/actions/health">
          <button type="submit" class="secondary">Check Health</button>
        </form>
      </div>
    </section>
    <section>
      <h2>Chat</h2>
      <form data-api="/api/chat">
        <label>Message <textarea name="message" required></textarea></label>
        <label>Level
          <select name="level">
            <option value="">Auto</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="expert">Expert</option>
          </select>
        </label>
        <button type="submit">Ask Wiki</button>
      </form>
    </section>
    <section>
      <h2>Result</h2>
      <pre id="result">Ready.</pre>
    </section>
  </main>
  <script>
    const result = document.querySelector("#result");
    for (const form of document.querySelectorAll("form[data-api]")) {{
      form.addEventListener("submit", async (event) => {{
        event.preventDefault();
        result.textContent = "Running...";
        const response = await fetch(form.dataset.api, {{
          method: "POST",
          body: new URLSearchParams(new FormData(form))
        }});
        const text = await response.text();
        try {{
          result.textContent = JSON.stringify(JSON.parse(text), null, 2);
        }} catch {{
          result.textContent = text;
        }}
      }});
    }}
  </script>
</body>
</html>
"""
