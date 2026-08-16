#!/usr/bin/env python3
"""Prepare a static frontend folder for a world without changing canon."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not world.exists():
        raise SystemExit(f"world does not exist: {world}")
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    return world


def resolve_output(world: Path, output_arg: str | None) -> Path:
    output = Path(output_arg).resolve() if output_arg else world / "frontend"
    try:
        output.relative_to(world)
    except ValueError as exc:
        raise SystemExit(f"frontend output must stay inside world directory: {output}") from exc
    return output


def copy_file(source: Path, target: Path, *, dry_run: bool, overwrite: bool) -> dict:
    item = {
        "source": str(source),
        "target": str(target),
        "exists": target.exists(),
        "copied": False,
        "skipped": False,
    }
    if not source.exists():
        item["skipped"] = True
        item["reason"] = "source missing"
        return item
    if target.exists() and not overwrite:
        item["skipped"] = True
        item["reason"] = "target exists; pass --overwrite to replace"
        return item
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        item["copied"] = True
    return item


def build_plan(world: Path, output: Path) -> list[tuple[Path, Path]]:
    template = skill_dir() / "assets" / "frontend-template"
    if not template.exists():
        raise SystemExit(f"frontend template missing: {template}")

    pairs: list[tuple[Path, Path]] = []
    for source in sorted(template.iterdir()):
        if source.is_file():
            pairs.append((source, output / source.name))
        elif source.is_dir():
            for nested in sorted(source.rglob("*")):
                if nested.is_file():
                    pairs.append((nested, output / nested.relative_to(template)))

    dashboard = world / "dashboard"
    pairs.extend(
        [
            (dashboard / "data.json", output / "dashboard.json"),
            (dashboard / "timeline.json", output / "timeline.json"),
            (dashboard / "map-layers.json", output / "map-layers.json"),
        ]
    )
    return pairs


def validate_json_outputs(output: Path) -> list[dict]:
    checks = []
    for name in ["dashboard.json", "timeline.json", "map-layers.json", "sample-dashboard.json", "sample-timeline.json", "sample-map-layers.json"]:
        path = output / name
        if not path.exists():
            checks.append({"file": name, "ok": False, "reason": "missing"})
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            checks.append({"file": name, "ok": False, "reason": str(exc)})
        else:
            checks.append({"file": name, "ok": True})
    return checks


def frontend_readme(world: Path, output: Path) -> str:
    world_rel = output.relative_to(world).as_posix()
    return "\n".join(
        [
            "# Be A God Frontend",
            "",
            "This folder is a static, observation-first frontend export for the current world.",
            "",
            "## Open",
            "",
            "- Open `index.html` in a browser.",
            "- Keep this folder beside `dashboard.json`, `timeline.json`, and `map-layers.json` for live world data.",
            "- If browser file loading is restricted, use the file picker buttons inside the page to load the three JSON exports manually.",
            "- For app mode with local API buttons, run `scripts/serve_frontend.py --world <world>` and open the printed localhost URL.",
            "",
            "## Data files",
            "",
            "- `dashboard.json`: time, weather, active branch, pending action requests, rules, random-log summary, attention summary, and warnings.",
            "- `timeline.json`: confirmed events plus lightweight locked-rule, queued/due, ignored-digest, and branch nodes.",
            "- `map-layers.json`: map layers, visible pieces, pins, and source pointers.",
            "- `sample-dashboard.json`, `sample-timeline.json`, `sample-map-layers.json`: fallback demo data from the skill template.",
            "",
            "## Canon boundary",
            "",
            "- This frontend is read-only for canon. It may show suggested commands or draft action payloads.",
            "- In app mode, buttons may create non-canonical action request support files through the local server.",
            "- Formal canon world changes still require Codex/player confirmation and the appropriate local settlement scripts.",
            "- Refresh this folder after world changes with:",
            "",
            "```powershell",
            f"python scripts/prepare_frontend.py --world <world> --output <world>/{world_rel} --confirmed --overwrite",
            "```",
            "",
        ]
    )


def write_readme(world: Path, output: Path, *, dry_run: bool, overwrite: bool) -> dict:
    target = output / "README.md"
    item = {
        "source": "generated frontend README",
        "target": str(target),
        "exists": target.exists(),
        "copied": False,
        "skipped": False,
    }
    if target.exists() and not overwrite:
        item["skipped"] = True
        item["reason"] = "target exists; pass --overwrite to replace"
        return item
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(frontend_readme(world, output), encoding="utf-8")
        item["copied"] = True
    return item


def prepare(world: Path, output: Path, *, dry_run: bool, confirmed: bool, overwrite: bool) -> dict:
    output = output.resolve()
    if not dry_run and not confirmed:
        raise SystemExit("refusing to write frontend files without --confirmed")
    if not output.is_relative_to(world):
        raise SystemExit(f"output must stay inside the world directory: {output}")
    if output.exists() and not output.is_dir():
        raise SystemExit(f"output exists but is not a directory: {output}")

    actions = [copy_file(source, target, dry_run=dry_run, overwrite=overwrite) for source, target in build_plan(world, output)]
    actions.append(write_readme(world, output, dry_run=dry_run, overwrite=overwrite))
    validation = [] if dry_run else validate_json_outputs(output)
    hard_failures = [
        item for item in actions
        if item["skipped"] and item.get("reason") not in {"source missing"}
    ]
    return {
        "ok": not hard_failures and all(item.get("ok", True) for item in validation),
        "world": str(world),
        "output": str(output),
        "dry_run": dry_run,
        "actions": actions,
        "json_validation": validation,
        "open": str(output / "index.html"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy the static frontend template and exported JSON into a world-local frontend folder.")
    parser.add_argument("--world", required=True, help="World directory containing ACTIVE.md.")
    parser.add_argument("--output", help="Output directory. Defaults to <world>/frontend.")
    parser.add_argument("--dry-run", action="store_true", help="Preview planned copies without writing.")
    parser.add_argument("--confirmed", action="store_true", help="Required for writing files.")
    parser.add_argument("--overwrite", action="store_true", help="Replace files in an existing frontend folder.")
    args = parser.parse_args()

    world = resolve_world(args.world)
    output = resolve_output(world, args.output)
    report = prepare(world, output, dry_run=args.dry_run, confirmed=args.confirmed, overwrite=args.overwrite)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
