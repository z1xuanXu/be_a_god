#!/usr/bin/env python3
"""Serve the be-a-god frontend with small world-local API endpoints."""

from __future__ import annotations

import argparse
import json
import mimetypes
import subprocess
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


SAFE_METHOD_SCRIPTS = {
    "build_map_layers.py",
    "build_timeline.py",
    "export_dashboard.py",
}


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def skill_dir() -> Path:
    return script_dir().parent


def resolve_world(raw: str) -> Path:
    world = Path(raw).resolve()
    if not world.is_dir() or not (world / "ACTIVE.md").exists():
        raise SystemExit(f"world must be a directory containing ACTIVE.md: {world}")
    return world


def resolve_frontend_root(world: Path, raw: str | None) -> Path:
    if raw:
        root = Path(raw).resolve()
    elif (world / "frontend" / "index.html").exists():
        root = (world / "frontend").resolve()
    else:
        root = (skill_dir() / "assets" / "frontend-template").resolve()
    if not (root / "index.html").exists():
        raise SystemExit(f"frontend root missing index.html: {root}")
    return root


def run_script(name: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    if name not in SAFE_METHOD_SCRIPTS and name not in {
        "create_action_request.py",
        "advance_world.py",
        "cancel_action_request.py",
        "reorder_action_requests.py",
        "set_map_brush.py",
    }:
        raise ValueError(f"unsupported script: {name}")
    return subprocess.run(
        [sys.executable, str(script_dir() / name), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def refresh_state(world: Path) -> None:
    for name, args in [
        ("build_map_layers.py", ["--world", str(world)]),
        ("build_timeline.py", ["--world", str(world)]),
        ("export_dashboard.py", ["--world", str(world)]),
    ]:
        completed = run_script(name, args)
        if completed.returncode != 0:
            raise RuntimeError(f"{name} failed: {completed.stderr or completed.stdout}")


def read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def state_payload(world: Path, refresh: bool) -> dict[str, Any]:
    if refresh:
        refresh_state(world)
    return {
        "ok": True,
        "world": str(world),
        "dashboard": read_json_file(world / "dashboard" / "data.json"),
        "timeline": read_json_file(world / "dashboard" / "timeline.json"),
        "map_layers": read_json_file(world / "dashboard" / "map-layers.json"),
    }


def as_str(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)


def action_request_args(world: Path, data: dict[str, Any]) -> list[str]:
    action = as_str(data.get("action")).strip()
    if not action:
        raise ValueError("action is required")
    args = ["--world", str(world), "--action", action]
    for key, flag in [
        ("target_id", "--target-id"),
        ("target_kind", "--target-kind"),
        ("target_source", "--target-source"),
        ("intent", "--intent"),
        ("text", "--text"),
        ("request_id", "--request-id"),
        ("preset", "--preset"),
        ("summary", "--summary"),
        ("value", "--value"),
    ]:
        value = data.get(key)
        if value not in (None, ""):
            args.extend([flag, as_str(value)])
    if data.get("days") not in (None, ""):
        args.extend(["--days", as_str(data["days"])])
    payload = data.get("payload")
    if payload not in (None, "", {}):
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        args.extend(["--payload-json", json.dumps(payload, ensure_ascii=False, separators=(",", ":"))])
    args.extend(["--confirmed", "--json"])
    return args


def create_action_request(world: Path, data: dict[str, Any]) -> dict[str, Any]:
    completed = run_script("create_action_request.py", action_request_args(world, data))
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    result = json.loads(completed.stdout)
    try:
        result["state"] = state_payload(world, refresh=True)
    except Exception as exc:  # noqa: BLE001 - API should report request creation even if refresh read fails.
        result["state_error"] = str(exc)
    return result


def advance_world_args(world: Path, data: dict[str, Any]) -> list[str]:
    args = ["--world", str(world)]
    for key, flag in [
        ("preset", "--preset"),
        ("summary", "--summary"),
    ]:
        value = data.get(key)
        if value not in (None, ""):
            args.extend([flag, as_str(value)])
    if data.get("days") not in (None, ""):
        args.extend(["--days", as_str(data["days"])])
    if data.get("ignore_queue"):
        args.append("--ignore-queue")
    if data.get("until_next_queue"):
        args.append("--until-next-queue")
    if data.get("wander") is True:
        args.append("--wander")
    elif data.get("wander") is False:
        args.append("--no-wander")
    if data.get("wander_limit") not in (None, ""):
        args.extend(["--wander-limit", as_str(data["wander_limit"])])
    if data.get("wander_exclude_ignored") is True:
        args.append("--wander-exclude-ignored")
    elif data.get("wander_exclude_ignored") is False:
        args.append("--wander-include-ignored")
    args.append("--confirmed")
    return args


def advance_world(world: Path, data: dict[str, Any]) -> dict[str, Any]:
    completed = run_script("advance_world.py", advance_world_args(world, data))
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    return {
        "ok": True,
        "stdout": completed.stdout.strip(),
        "state": state_payload(world, refresh=True),
    }


def cancel_action_request(world: Path, data: dict[str, Any]) -> dict[str, Any]:
    request_id = as_str(data.get("request_id")).strip()
    if not request_id:
        raise ValueError("request_id is required")
    reason = as_str(data.get("reason"), "cancelled by player")
    completed = run_script(
        "cancel_action_request.py",
        ["--world", str(world), "--request-id", request_id, "--reason", reason, "--confirmed", "--json"],
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    result = json.loads(completed.stdout)
    result["state"] = state_payload(world, refresh=True)
    return result


def reorder_action_requests(world: Path, data: dict[str, Any]) -> dict[str, Any]:
    request_ids = data.get("request_ids")
    if not isinstance(request_ids, list) or not request_ids:
        raise ValueError("request_ids must be a non-empty array")
    completed = run_script(
        "reorder_action_requests.py",
        [
            "--world",
            str(world),
            "--request-ids-json",
            json.dumps(request_ids, ensure_ascii=False, separators=(",", ":")),
            "--confirmed",
            "--json",
        ],
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    result = json.loads(completed.stdout)
    result["state"] = state_payload(world, refresh=True)
    return result


def apply_map_brush(world: Path, data: dict[str, Any]) -> dict[str, Any]:
    brush_id = as_str(data.get("brush_id")).strip()
    kind = as_str(data.get("kind")).strip()
    points_json = data.get("points_json")
    if not brush_id or not kind or points_json in (None, ""):
        raise ValueError("brush_id, kind, and points_json are required")
    if isinstance(points_json, list):
        points_json = json.dumps(points_json, ensure_ascii=False, separators=(",", ":"))
    args = [
        "--world", str(world), "--brush-id", brush_id, "--kind", kind,
        "--points-json", as_str(points_json), "--label", as_str(data.get("label"), brush_id),
        "--level", as_str(data.get("level"), "region"),
        "--width", as_str(data.get("width"), "5"),
        "--density", as_str(data.get("density"), "12"),
        "--jitter", as_str(data.get("jitter"), "2"), "--confirmed",
    ]
    if data.get("color"):
        args.extend(["--color", as_str(data["color"])])
    completed = run_script("set_map_brush.py", args)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    return {"ok": True, "brush_id": brush_id, "stdout": completed.stdout.strip(), "state": state_payload(world, refresh=True)}


class Handler(BaseHTTPRequestHandler):
    server_version = "BeAGodFrontend/0.1"

    def json_response(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def text_response(self, status: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @property
    def world(self) -> Path:
        return self.server.world  # type: ignore[attr-defined]

    @property
    def frontend_root(self) -> Path:
        return self.server.frontend_root  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            self.json_response(200, {"ok": True, "world": str(self.world), "frontend_root": str(self.frontend_root)})
            return
        if parsed.path == "/api/state":
            query = urllib.parse.parse_qs(parsed.query)
            refresh = query.get("refresh", ["1"])[0] != "0"
            try:
                self.json_response(200, state_payload(self.world, refresh=refresh))
            except Exception as exc:  # noqa: BLE001
                self.json_response(500, {"ok": False, "error": str(exc)})
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("request body must be a JSON object")
            if parsed.path == "/api/action-request":
                self.json_response(200, create_action_request(self.world, data))
                return
            if parsed.path == "/api/advance-world":
                self.json_response(200, advance_world(self.world, data))
                return
            if parsed.path == "/api/action-request/cancel":
                self.json_response(200, cancel_action_request(self.world, data))
                return
            if parsed.path == "/api/action-requests/reorder":
                self.json_response(200, reorder_action_requests(self.world, data))
                return
            if parsed.path == "/api/map-brush/apply":
                self.json_response(200, apply_map_brush(self.world, data))
                return
            self.json_response(404, {"ok": False, "error": "unknown API endpoint"})
        except Exception as exc:  # noqa: BLE001
            self.json_response(400, {"ok": False, "error": str(exc)})

    def serve_static(self, raw_path: str) -> None:
        rel = raw_path.lstrip("/") or "index.html"
        rel = urllib.parse.unquote(rel)
        target = (self.frontend_root / rel).resolve()
        try:
            target.relative_to(self.frontend_root)
        except ValueError:
            self.text_response(403, "forbidden")
            return
        if target.is_dir():
            target = target / "index.html"
        if not target.exists() or not target.is_file():
            self.text_response(404, "not found")
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type = f"{content_type}; charset=utf-8"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve a be-a-god world frontend and local API on localhost.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--frontend-root", help="Defaults to <world>/frontend if prepared, otherwise the skill template.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-refresh-start", action="store_true", help="Do not rebuild dashboard/timeline/map-layers before serving.")
    parser.add_argument("--check", action="store_true", help="Validate frontend app state and exit without starting the server.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    world = resolve_world(args.world)
    frontend_root = resolve_frontend_root(world, args.frontend_root)
    if args.check:
        payload = state_payload(world, refresh=not args.no_refresh_start)
        report = {
            "ok": True,
            "world": str(world),
            "frontend_root": str(frontend_root),
            "endpoints": [
                "/api/health",
                "/api/state",
                "/api/action-request",
                "/api/advance-world",
                "/api/action-request/cancel",
                "/api/action-requests/reorder",
            ],
            "state_keys": sorted(key for key in payload.keys() if key != "ok"),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if not args.no_refresh_start:
        refresh_state(world)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.world = world  # type: ignore[attr-defined]
    server.frontend_root = frontend_root  # type: ignore[attr-defined]
    url = f"http://{args.host}:{args.port}/"
    print(json.dumps({"ok": True, "url": url, "world": str(world), "frontend_root": str(frontend_root)}, ensure_ascii=False))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nserver stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
