import http.client
import json
from threading import Thread

from frontier_radar.cli import main
from frontier_radar.daily import DailyResult, ReviewItem, RunReview
from frontier_radar.web import create_server


def test_web_dashboard_exposes_local_actions(tmp_path):
    server = create_server(tmp_path, host="127.0.0.1", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request("GET", "/")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert response.status == 200
    assert "Frontier Radar" in body
    assert "Run Daily" in body
    assert "/api/actions/daily" in body
    assert "/api/chat" in body
    assert "frontier-radar serve" in body
    assert "formatResult" in body
    assert "Raw JSON" in body
    assert "Daily run" in body
    assert "Stop Server" in body
    assert "/api/actions/stop" in body


def test_web_daily_action_returns_json_result(tmp_path, monkeypatch):
    called = {}

    def fake_run_daily(root, budget_minutes=None, top_n=None):
        called["root"] = root
        called["budget_minutes"] = budget_minutes
        called["top_n"] = top_n
        return DailyResult(
            "ok",
            "wiki/daily/2026-06-22.md",
            {"manual": 1},
            [],
            ["agent note"],
            RunReview(
                1,
                1,
                0,
                {"manual": 1},
                ["wiki/daily/2026-06-22.md"],
                "test web daily",
                [ReviewItem("agent note", 3.0, {"relevance": 3.0})],
            ),
        )

    monkeypatch.setattr("frontier_radar.web.run_daily", fake_run_daily)
    server = create_server(tmp_path, host="127.0.0.1", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        payload = "budget_minutes=7&top_n=3"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request("POST", "/api/actions/daily", body=payload, headers=headers)
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert response.status == 200
    assert data["status"] == "ok"
    assert data["digest_path"] == "wiki/daily/2026-06-22.md"
    assert data["review"]["top_items"][0]["title"] == "agent note"
    assert called == {"root": tmp_path.resolve(), "budget_minutes": 7, "top_n": 3}


def test_web_rank_action_returns_json_result(tmp_path, monkeypatch):
    called = {}

    def fake_rank_payload(root, limit=20):
        called["root"] = root
        called["limit"] = limit
        return {"status": "ok", "items": [{"title": "ranked item"}]}

    monkeypatch.setattr("frontier_radar.web._rank_payload", fake_rank_payload)
    server = create_server(tmp_path, host="127.0.0.1", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        payload = "limit=5"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request("POST", "/api/actions/rank", body=payload, headers=headers)
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert response.status == 200
    assert data["items"][0]["title"] == "ranked item"
    assert called == {"root": tmp_path.resolve(), "limit": 5}


def test_web_stop_action_shuts_down_server(tmp_path):
    server = create_server(tmp_path, host="127.0.0.1", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request("POST", "/api/actions/stop", body="", headers=headers)
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        thread.join(timeout=5)
    finally:
        if thread.is_alive():
            server.shutdown()
            thread.join(timeout=5)
        server.server_close()

    assert response.status == 200
    assert data["status"] == "ok"
    assert "stopping" in data["message"]
    assert not thread.is_alive()


def test_cli_serve_invokes_local_web_service(monkeypatch, capsys):
    called = {}

    def fake_serve_web(root, host, port):
        called["root"] = root
        called["host"] = host
        called["port"] = port
        return 0

    monkeypatch.setattr("frontier_radar.cli.serve_web", fake_serve_web)

    exit_code = main(["--root", ".", "serve", "--host", "127.0.0.1", "--port", "8766"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert called["root"].name == "st"
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 8766
