#!/usr/bin/env python3
"""Parse and validate Local AI configuration without executing .env code."""
from __future__ import annotations

import argparse
import os
import re
import shlex
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
MODELS_FILE = ROOT / "config/models.toml"
KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")
BOOLS = {"true", "false"}
PORTS = (
    "OPEN_WEBUI_PORT", "LLAMA_SERVER_PORT", "EMBEDDING_SERVER_PORT",
    "TOOL_BRIDGE_PORT", "SEARXNG_PORT", "DOCLING_GATE_PORT", "DOCLING_PORT",
)
POSITIVE = (
    "DOCLING_GATE_POLL_SECONDS", "DOCLING_GATE_MAX_WAIT_SECONDS",
    "DOCLING_GATE_MAX_RETRIES", "DOCLING_GATE_MAX_UNKNOWN_POLLS",
    "DOCLING_MAX_SYNC_WAIT_SECONDS", "TOOL_MAX_OUTPUT_CHARS", "LOG_MAX_BYTES",
    "LOG_ROTATION_COUNT", "MODEL_CONTEXT_SIZE", "MODEL_PARALLELISM", "MODEL_THREADS",
    "MODEL_BATCH_SIZE", "MODEL_UBATCH_SIZE", "RAG_CHUNK_SIZE", "WEB_SEARCH_RESULT_COUNT",
    "WEB_SEARCH_CONCURRENT_REQUESTS", "WEB_LOADER_CONCURRENT_REQUESTS",
    "WEB_LOADER_TIMEOUT_SECONDS", "WEB_FETCH_MAX_CONTENT_LENGTH",
)
REQUIRED = (
    "LLAMA_IMAGE", "SEARXNG_IMAGE", "DOCLING_IMAGE", "MODEL_DIR", "OPEN_WEBUI_DATA_DIR",
    "SEARXNG_CACHE_DIR", "DOCLING_ARTIFACTS_DIR", "DOCLING_AUDIT_DIR", "LLAMA_API_KEY",
    "EMBEDDING_API_KEY", "SEARXNG_SECRET", "DOCLING_GATE_API_KEY", "WEBUI_SECRET_KEY",
)
PATHS = (
    "LLAMA_IMAGE", "TOOL_IMAGE", "SEARXNG_IMAGE", "DOCLING_IMAGE", "MODEL_DIR",
    "OPEN_WEBUI_DATA_DIR", "TOOL_AUDIT_DIR", "SEARXNG_CACHE_DIR", "DOCLING_ARTIFACTS_DIR",
    "DOCLING_AUDIT_DIR", "WORKSPACE_DIR", "TOOL_DATA_DIR",
)


class ConfigError(ValueError):
    pass


def parse_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ConfigError("Missing .env; copy .env.example first.")
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f".env:{number}: expected KEY=value")
        name, value = line.split("=", 1)
        if not KEY.fullmatch(name):
            raise ConfigError(f".env:{number}: invalid key {name!r}")
        if name in values:
            raise ConfigError(f".env:{number}: duplicate key {name}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name] = value
    return values


def integer(values: dict[str, str], name: str, *, minimum: int = 1) -> None:
    raw = values.get(name, "")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if value < minimum:
        qualifier = "non-negative" if minimum == 0 else f">= {minimum}"
        raise ConfigError(f"{name} must be {qualifier}")


def resolve(value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return str(path.resolve(strict=False))


def load_models() -> dict[str, dict[str, str]]:
    try:
        parsed = tomllib.loads(MODELS_FILE.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"Invalid {MODELS_FILE.relative_to(ROOT)}: {exc}") from exc
    result: dict[str, dict[str, str]] = {}
    for role in ("chat", "embedding"):
        entry = parsed.get(role)
        if not isinstance(entry, dict):
            raise ConfigError(f"models.toml requires [{role}]")
        for field in ("role", "repo", "filename", "sha256", "alias"):
            if not isinstance(entry.get(field), str):
                raise ConfigError(f"models.toml [{role}].{field} must be a string")
        if entry["role"] != role or not entry["repo"] or not entry["filename"] or not entry["alias"]:
            raise ConfigError(f"models.toml [{role}] is incomplete")
        checksum = entry["sha256"]
        if checksum and not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ConfigError(f"models.toml [{role}].sha256 must be empty or a SHA-256")
        result[role] = {key: str(value) for key, value in entry.items()}
    return result


def validate(values: dict[str, str]) -> dict[str, str]:
    defaults = {
        "TOOL_BRIDGE_ENABLED": "false", "TOOL_DATA_DIR": "", "TOOL_HIDDEN_PATHS": "",
        "DOCLING_GATE_IDLE_SECONDS": "10", "DOCLING_GATE_MAX_UNKNOWN_POLLS": "3",
        "LOG_MAX_BYTES": "10485760", "LOG_ROTATION_COUNT": "5", "APPTAINER_BIN": "",
    }
    for key, value in defaults.items():
        values.setdefault(key, value)
    missing = [name for name in REQUIRED if not values.get(name)]
    if missing:
        raise ConfigError("Missing required setting(s): " + ", ".join(missing))
    for name in ("TOOL_BRIDGE_ENABLED", "WEB_SEARCH_ENABLED"):
        if values.get(name, "") not in BOOLS:
            raise ConfigError(f"{name} must be true or false")
    seen: set[int] = set()
    for name in PORTS:
        integer(values, name)
        port = int(values[name])
        if port > 65535 or port in seen:
            raise ConfigError(f"{name} must be a unique port in 1..65535")
        seen.add(port)
    for name in POSITIVE:
        if name in values:
            integer(values, name)
    integer(values, "DOCLING_GATE_IDLE_SECONDS", minimum=0)
    if values["TOOL_BRIDGE_ENABLED"] == "true":
        for name in ("TOOL_IMAGE", "TOOL_SANDBOX_API_KEY", "TOOL_AUDIT_DIR", "WORKSPACE_DIR", "TOOL_WRITE_MODE", "TOOL_NETWORK_MODE"):
            if not values.get(name):
                raise ConfigError(f"{name} is required when TOOL_BRIDGE_ENABLED=true")
        if values["TOOL_WRITE_MODE"] not in {"read_only", "read_write"}:
            raise ConfigError("TOOL_WRITE_MODE must be read_only or read_write")
        if values["TOOL_NETWORK_MODE"] not in {"isolated", "unverified"}:
            raise ConfigError("TOOL_NETWORK_MODE must be isolated or unverified")
    for name in PATHS:
        if values.get(name):
            values[name] = resolve(values[name])
    if values["TOOL_BRIDGE_ENABLED"] == "true" and values.get("TOOL_DATA_DIR") and not Path(values["TOOL_DATA_DIR"]).is_dir():
        raise ConfigError("TOOL_DATA_DIR must name an existing directory")
    if values["TOOL_BRIDGE_ENABLED"] == "true" and not Path(values["WORKSPACE_DIR"]).is_dir() and Path(values["WORKSPACE_DIR"]).exists():
        raise ConfigError("WORKSPACE_DIR must be a directory")
    models = load_models()
    for env_name, role in (("MODEL_FILE", "chat"), ("EMBEDDING_MODEL_FILE", "embedding")):
        legacy = values.get(env_name)
        if legacy and legacy != models[role]["filename"]:
            raise ConfigError(f"{env_name} is deprecated and conflicts with config/models.toml")
    values["MODEL_FILE"] = models["chat"]["filename"]
    values["EMBEDDING_MODEL_FILE"] = models["embedding"]["filename"]
    values["CHAT_MODEL_ALIAS"] = models["chat"]["alias"]
    values["EMBEDDING_MODEL_ALIAS"] = models["embedding"]["alias"]
    values["LOCAL_AI_ROOT"] = str(ROOT)
    return values


def emit_shell(values: dict[str, str]) -> str:
    return "\n".join(f"export {key}={shlex.quote(value)}" for key, value in sorted(values.items())) + "\n"


def emit_systemd(values: dict[str, str]) -> str:
    # Quote whitespace and shell-significant values; systemd EnvironmentFile accepts this subset.
    def quoted(value: str) -> str:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "") + '"'
    return "\n".join(f"{key}={quoted(value)}" for key, value in sorted(values.items())) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shell", action="store_true")
    parser.add_argument("--write-systemd-env", action="store_true")
    args = parser.parse_args()
    try:
        raw_values = parse_env(ENV_FILE)
        values = validate(raw_values)
        if not args.shell:
            for name in ("MODEL_FILE", "EMBEDDING_MODEL_FILE"):
                if name in raw_values:
                    print(f"Warning: {name} is deprecated; use config/models.toml.", file=sys.stderr)
        if args.write_systemd_env:
            output = ROOT / "run/local-ai.env"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(emit_systemd(values), encoding="utf-8")
            os.chmod(output, 0o600)
        if args.shell:
            sys.stdout.write(emit_shell(values))
        elif not args.write_systemd_env:
            print("Configuration is valid.")
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
