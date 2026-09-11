"""Narrow localhost bridge from Open WebUI to a contained Apptainer tool SIF."""
from __future__ import annotations

import asyncio
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

APP = FastAPI(title="Local AI Restricted Tool Bridge", version="0.1.0")
BEARER = HTTPBearer(auto_error=False)
UI_PORT = os.environ.get("OPEN_WEBUI_PORT", "3000")
APP.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://127.0.0.1:{UI_PORT}", f"http://localhost:{UI_PORT}"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


class RunRequest(BaseModel):
    command: str = Field(min_length=1, max_length=8000)
    mode: Literal["read", "write"] = "read"
    timeout_seconds: int = Field(default=30, ge=1, le=300)


def setting(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"missing required bridge setting: {name}")
    return value


def optional_setting(name: str) -> str:
    return os.environ.get(name, "").strip()


def output_limit() -> int:
    raw_limit = optional_setting("TOOL_MAX_OUTPUT_CHARS") or "6000"
    try:
        limit = int(raw_limit)
    except ValueError as error:
        raise RuntimeError("TOOL_MAX_OUTPUT_CHARS must be a positive integer") from error
    if limit < 1:
        raise RuntimeError("TOOL_MAX_OUTPUT_CHARS must be a positive integer")
    return limit


def truncate_tail(value: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    if limit < 48:
        return value[-limit:]
    marker = "\n...[output truncated]\n"
    return marker + value[-(limit - len(marker)):]


def limit_output(stdout: str, stderr: str) -> tuple[str, str]:
    """Bound the total command output returned to the model and audit log."""
    limit = output_limit()
    total = len(stdout) + len(stderr)
    if total <= limit:
        return stdout, stderr
    if not stdout:
        return "", truncate_tail(stderr, limit)
    if not stderr:
        return truncate_tail(stdout, limit), ""
    stdout_limit = max(1, limit * len(stdout) // total)
    return truncate_tail(stdout, stdout_limit), truncate_tail(stderr, limit - stdout_limit)


def bind_hidden_paths(command: list[str], workspace: Path) -> None:
    """Mask explicitly listed files below /workspace with an empty read-only file."""
    configured = optional_setting("TOOL_HIDDEN_PATHS")
    if not configured:
        return
    mask = Path(setting("TOOL_AUDIT_DIR")) / "empty-secret-mask"
    mask.parent.mkdir(parents=True, exist_ok=True)
    mask.touch(exist_ok=True)
    mask.chmod(0o600)
    for raw_path in configured.split(":"):
        candidate = Path(raw_path).expanduser().resolve()
        if not candidate.is_file():
            raise RuntimeError(f"TOOL_HIDDEN_PATHS entry is not a file: {candidate}")
        try:
            relative = candidate.relative_to(workspace)
        except ValueError as error:
            raise RuntimeError(f"TOOL_HIDDEN_PATHS entry is outside WORKSPACE_DIR: {candidate}") from error
        command.extend(["--bind", f"{mask}:/workspace/{relative}:ro"])


def audit(event: dict) -> None:
    directory = Path(setting("TOOL_AUDIT_DIR"))
    directory.mkdir(parents=True, exist_ok=True)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from log_rotate import rotate_from_environment
    target = directory / "tool-bridge.jsonl"
    rotate_from_environment(target)
    with target.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def require_key(credentials: HTTPAuthorizationCredentials | None) -> None:
    expected = setting("TOOL_SANDBOX_API_KEY")
    supplied = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else ""
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="invalid tool bridge API key")


@APP.get("/health")
@APP.get("/health/live")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@APP.get("/health/ready")
async def ready() -> dict[str, str]:
    try:
        runtime = Path(setting("APPTAINER_BIN"))
        if not runtime.is_absolute() and not __import__("shutil").which(str(runtime)):
            raise RuntimeError("Apptainer runtime is unavailable")
        if not Path(setting("TOOL_IMAGE")).is_file():
            raise RuntimeError("tool image is unavailable")
        if not Path(setting("WORKSPACE_DIR")).is_dir():
            raise RuntimeError("workspace is unavailable")
        data_directory = optional_setting("TOOL_DATA_DIR")
        if data_directory and not Path(data_directory).is_dir():
            raise RuntimeError("tool data directory is unavailable")
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"status": "ready"}


@APP.post("/run")
async def run_tool(payload: RunRequest, credentials: HTTPAuthorizationCredentials | None = Depends(BEARER)) -> dict:
    require_key(credentials)
    if payload.mode == "write" and os.environ.get("TOOL_WRITE_MODE") != "read_write":
        raise HTTPException(status_code=403, detail="workspace write mode is disabled")
    started = datetime.now(timezone.utc)
    started_monotonic = asyncio.get_running_loop().time()
    response: dict = {"exit_code": 125, "stdout": "", "stderr": "internal bridge error"}
    failure: str | None = None
    try:
        workspace_path = Path(setting("WORKSPACE_DIR")).resolve()
        if not workspace_path.is_dir():
            raise RuntimeError(f"WORKSPACE_DIR is not a directory: {workspace_path}")
        workspace = str(workspace_path)
        image = str(Path(setting("TOOL_IMAGE")).resolve())
        if not Path(image).is_file():
            raise RuntimeError(f"TOOL_IMAGE is not a file: {image}")
        bind_mode = "rw" if payload.mode == "write" else "ro"
        command = [setting("APPTAINER_BIN"), "exec", "--cleanenv", "--containall", "--no-home",
                   "--writable-tmpfs", "--pwd", "/workspace", "--bind", f"{workspace}:/workspace:{bind_mode}"]
        data_directory = optional_setting("TOOL_DATA_DIR")
        if data_directory:
            data_path = Path(data_directory).resolve()
            if not data_path.is_dir():
                raise RuntimeError(f"TOOL_DATA_DIR is not a directory: {data_path}")
            command.extend(["--bind", f"{data_path}:/data:ro"])
        bind_hidden_paths(command, workspace_path)
        if os.environ.get("TOOL_NETWORK_MODE") == "isolated":
            command.extend(["--net", "--network", "none"])
        command.extend([image, "/bin/sh", "-lc", payload.command])
        result = await asyncio.to_thread(
            __import__("subprocess").run, command, text=True, capture_output=True,
            timeout=payload.timeout_seconds, check=False,
        )
        stdout, stderr = limit_output(result.stdout, result.stderr)
        response = {"exit_code": result.returncode, "stdout": stdout, "stderr": stderr}
    except __import__("subprocess").TimeoutExpired:
        response = {"exit_code": 124, "stdout": "", "stderr": f"timed out after {payload.timeout_seconds} seconds"}
    except (OSError, RuntimeError) as error:
        failure = str(error)
        response = {"exit_code": 125, "stdout": "", "stderr": failure}
    audit({"at": started.isoformat(), "mode": payload.mode, "command": payload.command,
           "duration_ms": round((asyncio.get_running_loop().time() - started_monotonic) * 1000),
           "timeout": response["exit_code"] == 124, "failure": failure, **response})
    if failure:
        raise HTTPException(status_code=503, detail="tool bridge configuration or runtime failure")
    return response
