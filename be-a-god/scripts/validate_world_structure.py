#!/usr/bin/env python3
"""Validate the minimal be-a-god world directory structure."""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED = [
    "WORLD.md",
    "ACTIVE.md",
    "CANON.md",
    "PLAYER.md",
    "story/STORY-TREE.md",
    "story/main/SAVE.md",
    "story/main/CURRENT.md",
    "story/main/events",
    "story/main/state",
    "story/main/chronicle",
    "story/main/random",
    "story/main/runtime",
    "story/main/checkpoints",
    "system",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", help="Path to worlds/<world-id>")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    missing = []
    for rel in REQUIRED:
        if not (world / rel).exists():
            missing.append(rel)

    if missing:
        print("Missing required paths:")
        for rel in missing:
            print(f"- {rel}")
        return 1

    print(f"World structure OK: {world}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
