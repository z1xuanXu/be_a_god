#!/usr/bin/env python3
"""Run one external-model play turn without directly mutating canon."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
SCHEMA = "be-a-god.external-model-run.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def script_path(name: str) -> str:
    return str(Path(__file__).resolve().parent / name)


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def resolve_world(raw: str) -> Path:
    world = Path(raw).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    return world


def relative_inside(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit(f"Path is outside world directory: {path}") from exc


def parse_active(world: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    return data


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return subprocess.run(
        [sys.executable, *args],
        check=True,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


def refresh_manifest(world: Path) -> None:
    run_command([script_path("build_file_manifest.py"), str(world)])


def resolve_packet_path(world: Path, packet_arg: str) -> str:
    active = parse_active(world)
    candidate = Path(packet_arg)
    if candidate.exists():
        resolved = candidate.resolve()
    elif "/" in packet_arg or "\\" in packet_arg or packet_arg.endswith(".json"):
        resolved = (world / packet_arg).resolve()
    else:
        packet_id = validate_id(packet_arg, "--packet")
        resolved = world / active["branch_path"] / "runtime" / "interaction-packets" / f"{packet_id}.json"
    if not resolved.exists():
        raise SystemExit(f"Interaction packet not found: {packet_arg}")
    return relative_inside(resolved, world)


def build_or_load_packet(args: argparse.Namespace, world: Path, run_dir: Path | None) -> tuple[dict[str, Any], str | None]:
    if args.packet:
        rel = resolve_packet_path(world, args.packet)
        return read_json(world / rel), rel

    if not args.target_id or not args.intent:
        raise SystemExit("Provide --packet, or provide --target-id and --intent so a compact interaction packet can be built.")

    command = [
        script_path("make_interaction_packet.py"),
        "--world",
        str(world),
        "--target-id",
        args.target_id,
        "--target-kind",
        args.target_kind,
        "--intent",
        args.intent,
        "--mode",
        args.mode,
    ]
    if args.packet_id:
        command.extend(["--packet-id", validate_id(args.packet_id, "--packet-id")])
    if args.request_id:
        command.extend(["--request-id", validate_id(args.request_id, "--request-id")])
    if args.confirmed:
        completed = run_command(command)
        match = re.search(r"Wrote interaction packet:\s*(.+)", completed.stdout)
        if not match:
            raise SystemExit(f"Could not read packet path from make_interaction_packet.py output: {completed.stdout}")
        packet_path = Path(match.group(1).strip()).resolve()
        rel = relative_inside(packet_path, world)
        return read_json(packet_path), rel

    completed = run_command([*command, "--dry-run"])
    packet = json.loads(completed.stdout)
    if run_dir:
        write_json(run_dir / "packet.preview.json", packet)
    return packet, None


def extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    candidates = [stripped]
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(fenced)
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        candidates.append(text[first : last + 1])
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def validate_candidate(result_path: Path, kind: str) -> tuple[bool, dict[str, Any] | str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    completed = subprocess.run(
        [
            sys.executable,
            script_path("validate_settlement_result.py"),
            "--result",
            str(result_path),
            "--kind",
            kind,
            "--json",
        ],
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if completed.returncode != 0:
        return False, (completed.stderr + completed.stdout).strip()
    return True, json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one be-a-god turn through an external OpenAI-compatible model API without direct canon writes.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--packet", help="Existing world-local interaction packet path or packet id.")
    parser.add_argument("--target-id", help="Target id when a new interaction packet should be built.")
    parser.add_argument("--target-kind", default="unknown", choices=["character", "location", "object", "place", "event", "piece", "unknown"])
    parser.add_argument("--intent", help="Player intent when a new interaction packet should be built.")
    parser.add_argument("--mode", default="close-up", choices=["close-up", "observe", "dialogue", "intervene"])
    parser.add_argument("--packet-id", help="Optional packet id when creating a new packet.")
    parser.add_argument("--request-id", help="Optional action request id to attach when creating a new packet.")
    parser.add_argument("--prompt", default="Resolve this be-a-god turn. Return concise prose plus a JSON settlement result with visible_narration, gm_summary, and settlement_plan.")
    parser.add_argument("--settlement-kind", default="interaction", choices=["interaction", "queued-event", "settlement"])
    parser.add_argument("--run-id", help="Optional support-run id.")
    parser.add_argument("--call", action="store_true", help="Actually call the configured API. Omit for dry-run preview.")
    parser.add_argument("--confirmed", action="store_true", help="Write support run files and packet files. Does not settle canon.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    world = resolve_world(args.world)
    active = parse_active(world)
    run_id = validate_id(args.run_id or "EXT-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"), "--run-id")
    run_dir = world / active["branch_path"] / "runtime" / "external-model-runs" / run_id if args.confirmed else None

    packet, packet_rel = build_or_load_packet(args, world, run_dir)
    packet_for_call = packet_rel
    if packet_for_call is None:
        if run_dir is None:
            temp_packet = world / active["branch_path"] / "runtime" / "external-model-runs" / run_id / "packet.preview.json"
            packet_for_call = relative_inside(temp_packet, world)
        else:
            packet_for_call = relative_inside(run_dir / "packet.preview.json", world)

    if run_dir and not (run_dir / "packet.preview.json").exists() and packet_rel:
        write_json(run_dir / "packet.used.json", packet)

    call_args = [
        script_path("call_llm.py"),
        "--world",
        str(world),
        "--packet",
        packet_for_call,
        "--prompt",
        args.prompt,
        "--json",
    ]
    if args.call:
        call_args.append("--call")

    if not args.confirmed and packet_rel is None:
        report = {
            "ok": True,
            "mode": "plan",
            "canonical_effect": "none",
            "message": "Run again with --confirmed to write a support run packet, or provide --packet for an existing packet.",
            "would_call": call_args,
            "packet_preview": packet,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    completed = run_command(call_args)
    llm_report = json.loads(completed.stdout)
    candidate_info: dict[str, Any] | None = None
    next_commands: list[str] = []

    if run_dir:
        write_json(run_dir / "external-run.json", {
            "schema": SCHEMA,
            "run_id": run_id,
            "created_at": utc_now(),
            "world": str(world),
            "branch_path": active["branch_path"],
            "packet": packet_rel or relative_inside(run_dir / "packet.preview.json", world),
            "mode": "call" if args.call else "dry-run",
            "canonical_effect": "none",
            "prompt": args.prompt,
        })
        write_json(run_dir / "llm-response.json", llm_report)

    if args.call:
        text = str(llm_report.get("text") or "")
        if run_dir:
            write_text(run_dir / "model-output.txt", text)
        candidate = extract_json_object(text)
        if candidate and run_dir:
            candidate_path = run_dir / "settlement-result.candidate.json"
            write_json(candidate_path, candidate)
            ok, validation = validate_candidate(candidate_path, args.settlement_kind)
            candidate_info = {"path": relative_inside(candidate_path, world), "valid": ok, "validation": validation}
            if ok and packet_rel:
                next_commands.append(f"scripts/settle_interaction.py --world {world} --packet {packet_rel} --result {relative_inside(candidate_path, world)} --dry-run")
                next_commands.append(f"scripts/settle_interaction.py --world {world} --packet {packet_rel} --result {relative_inside(candidate_path, world)} --confirmed")
        elif run_dir:
            candidate_info = {"valid": False, "validation": "No JSON object found in model output."}
    else:
        next_commands.append(f"scripts/external_play_turn.py --world {world} --packet {packet_for_call} --prompt <instruction> --call --confirmed")

    report = {
        "ok": True,
        "run_id": run_id,
        "mode": "call" if args.call else "dry-run",
        "canonical_effect": "none",
        "run_dir": str(run_dir) if run_dir else None,
        "packet": packet_rel,
        "llm": llm_report,
        "candidate_settlement_result": candidate_info,
        "next_commands": next_commands,
    }
    if run_dir:
        refresh_manifest(world)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
