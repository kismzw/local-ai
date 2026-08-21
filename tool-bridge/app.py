"""Narrow localhost bridge from Open WebUI to a contained Apptainer tool SIF."""
from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

APP = FastAPI(title="Local AI Restricted Tool Bridge", version="0.1.0")
FORBIDDEN = re.compile(r"(?:^|[;&|\s])(sudo|su|mount|umount|systemctl|apt(?:-get)?|docker|podman|apptainer|reboot|shutdown)(?:\s|$)|rm\s+-[^\n]*(?:r|f)|git\s+(?:push|clean|reset\s+--hard)", re.I)


class RunRequest(BaseModel):
    command: str = Field(min_length=1, max_length=8000)
    mode: Literal["read", "write"] = "read"
    timeout_seconds: int = Field(default=30, ge=1, le=300)


def setting(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"missing required bridge setting: {name}")
    return value


def audit(event: dict) -> None:
    directory = Path(setting("TOOL_AUDIT_DIR"))
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "tool-bridge.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def require_key(authorization: str | None) -> None:
    expected = f"Bearer {setting('TOOL_SANDBOX_API_KEY')}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="invalid tool bridge API key")


@APP.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@APP.post("/run")
async def run_tool(payload: RunRequest, authorization: str | None = Header(default=None)) -> dict:
    require_key(authorization)
    if FORBIDDEN.search(payload.command):
        raise HTTPException(status_code=403, detail="command violates restricted tool policy")
    if payload.mode == "write" and os.environ.get("TOOL_WRITE_MODE") != "read_write":
        raise HTTPException(status_code=403, detail="workspace write mode is disabled")

    workspace = str(Path(setting("WORKSPACE_DIR")).resolve())
    image = str(Path(setting("TOOL_IMAGE")).resolve())
    bind_mode = "rw" if payload.mode == "write" else "ro"
    command = [
        setting("APPTAINER_BIN"), "exec", "--cleanenv", "--containall", "--no-home",
        "--writable-tmpfs", "--pwd", "/workspace", "--bind", f"{workspace}:/workspace:{bind_mode}",
    ]
    if os.environ.get("TOOL_NETWORK_MODE") == "isolated":
        command.extend(["--net", "--network", "none"])
    command.extend([image, "/bin/sh", "-lc", payload.command])
    started = datetime.now(timezone.utc)
    try:
        result = await asyncio.to_thread(
            __import__("subprocess").run, command, text=True, capture_output=True,
            timeout=payload.timeout_seconds, check=False,
        )
        response = {"exit_code": result.returncode, "stdout": result.stdout[-20000:], "stderr": result.stderr[-20000:]}
    except __import__("subprocess").TimeoutExpired:
        response = {"exit_code": 124, "stdout": "", "stderr": f"timed out after {payload.timeout_seconds} seconds"}
    audit({"at": started.isoformat(), "mode": payload.mode, "command": payload.command, **response})
    return response
