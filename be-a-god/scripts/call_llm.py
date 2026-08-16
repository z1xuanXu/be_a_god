#!/usr/bin/env python3
"""Call an OpenAI-compatible LLM endpoint from visible be-a-god config."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SCHEMA = "be-a-god.llm-api-config.v1"


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return data


def resolve_world(path: str | None) -> Path | None:
    if not path:
        return None
    world = Path(path).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"World directory not found: {world}")
    return world


def resolve_world_local(world: Path, raw_path: str, field: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        candidate = path.resolve()
    else:
        candidate = (world / path).resolve()
    try:
        candidate.relative_to(world.resolve())
    except ValueError as exc:
        raise SystemExit(f"{field} must stay inside world directory: {raw_path}") from exc
    if not candidate.exists() or not candidate.is_file():
        raise SystemExit(f"{field} file not found: {candidate}")
    return candidate


def summarize_narrative_profile(world: Path | None) -> dict[str, Any] | None:
    if not world:
        return None
    path = world / "setup" / "narrative-profile.json"
    if not path.exists():
        return None
    data = read_json(path)
    profiles = data.get("profiles", {})
    default_profile = data.get("default_profile")
    if not isinstance(profiles, dict) or default_profile not in profiles:
        return None
    profile = profiles.get(default_profile)
    if not isinstance(profile, dict):
        return None
    output_layers = profile.get("output_layers", {})
    balance = profile.get("balance", {})
    return {
        "source": path.relative_to(world).as_posix(),
        "default_profile": default_profile,
        "label": profile.get("label"),
        "default_scale": balance.get("default_scale") if isinstance(balance, dict) else None,
        "priority_order": profile.get("priority_order", []),
        "required_output_layers": output_layers.get("required", []) if isinstance(output_layers, dict) else [],
        "event_pressure_sources": profile.get("event_pressure_sources", []),
        "event_chain": profile.get("event_chain", []),
        "style_avoid": profile.get("style", {}).get("avoid", []) if isinstance(profile.get("style"), dict) else [],
    }


def load_config(args: argparse.Namespace, world: Path | None) -> tuple[dict[str, Any], Path]:
    if args.config:
        config_path = Path(args.config).resolve()
    elif world:
        config_path = world / "setup" / "llm-api.config.json"
    else:
        raise SystemExit("Provide --config or --world so the LLM API config can be found.")
    if not config_path.exists():
        raise SystemExit(f"LLM API config not found: {config_path}")
    config = read_json(config_path)
    validate_config(config, str(config_path))
    return config, config_path


def validate_config(config: dict[str, Any], rel: str = "llm-api.config.json") -> None:
    if config.get("schema") != SCHEMA:
        raise SystemExit(f"{rel} schema must be {SCHEMA}")
    if config.get("protocol") != "openai-chat-completions":
        raise SystemExit(f"{rel} currently supports protocol=openai-chat-completions")
    base_url = config.get("base_url")
    if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
        raise SystemExit(f"{rel} base_url must start with http:// or https://")
    endpoint_path = config.get("endpoint_path", "/chat/completions")
    if not isinstance(endpoint_path, str) or not endpoint_path.startswith("/"):
        raise SystemExit(f"{rel} endpoint_path must start with /")
    if not isinstance(config.get("model"), str) or not config.get("model").strip():
        raise SystemExit(f"{rel} model must be a non-empty string")
    for key in ["temperature", "max_tokens", "timeout_seconds"]:
        value = config.get(key)
        if not isinstance(value, (int, float)) or value < 0:
            raise SystemExit(f"{rel} {key} must be a non-negative number")
    if "headers" in config and not isinstance(config.get("headers"), dict):
        raise SystemExit(f"{rel} headers must be an object")


def collect_prompt(args: argparse.Namespace, world: Path | None) -> str:
    parts: list[str] = []
    narrative_profile = summarize_narrative_profile(world)
    if narrative_profile:
        parts.append("## Narrative profile\n")
        parts.append(json.dumps(narrative_profile, ensure_ascii=False, indent=2))
        parts.append(
            "Use this profile for meaningful events: preserve causality and continuity, keep character agency, use historical texture, and return a concrete settlement plan instead of prose alone."
        )
    if args.packet:
        if not world:
            raise SystemExit("--packet requires --world so packet paths stay world-local")
        packet_path = resolve_world_local(world, args.packet, "--packet")
        packet_text = packet_path.read_text(encoding="utf-8")
        parts.append("## Supplied game packet\n")
        parts.append(packet_text)
    if args.prompt_file:
        prompt_path = Path(args.prompt_file).resolve()
        if world:
            prompt_path = resolve_world_local(world, args.prompt_file, "--prompt-file")
        if not prompt_path.exists() or not prompt_path.is_file():
            raise SystemExit(f"--prompt-file not found: {prompt_path}")
        parts.append("## Host prompt\n")
        parts.append(prompt_path.read_text(encoding="utf-8"))
    if args.prompt:
        parts.append("## Player prompt\n")
        parts.append(args.prompt)
    if not parts:
        raise SystemExit("Provide --prompt, --prompt-file, or --packet.")
    return "\n\n".join(parts)


def build_payload(config: dict[str, Any], prompt: str) -> dict[str, Any]:
    return {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": str(config.get("system_prompt") or "")},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.get("temperature", 0.8),
        "max_tokens": config.get("max_tokens", 1200),
    }


def endpoint(config: dict[str, Any]) -> str:
    return str(config["base_url"]).rstrip("/") + str(config.get("endpoint_path", "/chat/completions"))


def api_key(config: dict[str, Any]) -> str:
    env_name = str(config.get("api_key_env") or "").strip()
    value = os.environ.get(env_name, "") if env_name else ""
    if not value:
        value = str(config.get("api_key") or "")
    if not value:
        raise SystemExit("Missing API key. Set the configured environment variable or fill api_key in the local config.")
    return value


def sanitized_config(config: dict[str, Any]) -> dict[str, Any]:
    clean = dict(config)
    if clean.get("api_key"):
        clean["api_key"] = "<redacted>"
    return clean


def call_endpoint(config: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key(config)}"}
    for key, value in (config.get("headers") or {}).items():
        headers[str(key)] = str(value)
    request = urllib.request.Request(
        endpoint(config),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=float(config.get("timeout_seconds", 60))) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"LLM API HTTP {exc.code}: {body[:2000]}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"LLM API request failed: {exc}") from exc
    return json.loads(body)


def extract_text(response: dict[str, Any]) -> str:
    try:
        return str(response["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        return json.dumps(response, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Use a visible OpenAI-compatible LLM API config for be-a-god play outside Codex.")
    parser.add_argument("--world", help="World directory. Defaults config to setup/llm-api.config.json.")
    parser.add_argument("--config", help="Explicit LLM API config JSON.")
    parser.add_argument("--packet", help="World-local packet/result context file to include in the prompt.")
    parser.add_argument("--prompt-file", help="Prompt file. If --world is set, the path must stay inside the world.")
    parser.add_argument("--prompt", help="Inline player or host prompt.")
    parser.add_argument("--call", action="store_true", help="Actually call the configured API. Omit for dry-run preview.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    args = parser.parse_args()

    world = resolve_world(args.world)
    config, config_path = load_config(args, world)
    prompt = collect_prompt(args, world)
    payload = build_payload(config, prompt)
    preview = {
        "ok": True,
        "mode": "call" if args.call else "dry-run",
        "config_path": str(config_path),
        "endpoint": endpoint(config),
        "config": sanitized_config(config),
        "request": payload,
        "instruction": "Use --call to send this request. Dry-run does not contact the API.",
    }
    if not args.call:
        print(json.dumps(preview, ensure_ascii=False, indent=2) if args.json else json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    response = call_endpoint(config, payload)
    result = {"ok": True, "endpoint": endpoint(config), "text": extract_text(response), "raw_response": response}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
