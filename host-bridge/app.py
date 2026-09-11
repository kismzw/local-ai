"""Explicit opt-in localhost bridge for arbitrary commands as the owner user."""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

APP = FastAPI(title="Local AI Full Desktop Host Bridge", version="0.1.0")
BEARER = HTTPBearer(auto_error=False)
HOST_LOCK = asyncio.Lock()
UI_PORT = os.environ.get("OPEN_WEBUI_PORT", "3000")
APP.add_middleware(CORSMiddleware, allow_origins=[f"http://127.0.0.1:{UI_PORT}", f"http://localhost:{UI_PORT}"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])


class RunRequest(BaseModel):
    command: str = Field(min_length=1, max_length=8000)
    timeout_seconds: int = Field(default=30, ge=1, le=300)


def setting(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"missing required host bridge setting: {name}")
    return value


def output_limit() -> int:
    try:
        value = int(setting("HOST_TOOL_MAX_OUTPUT_CHARS"))
    except ValueError as error:
        raise RuntimeError("HOST_TOOL_MAX_OUTPUT_CHARS must be a positive integer") from error
    if value < 1:
        raise RuntimeError("HOST_TOOL_MAX_OUTPUT_CHARS must be a positive integer")
    return value


def max_timeout() -> int:
    try:
        value = int(setting("HOST_TOOL_MAX_TIMEOUT_SECONDS"))
    except ValueError as error:
        raise RuntimeError("HOST_TOOL_MAX_TIMEOUT_SECONDS must be a positive integer") from error
    if not 1 <= value <= 3600:
        raise RuntimeError("HOST_TOOL_MAX_TIMEOUT_SECONDS must be in 1..3600")
    return value


def limit_output(stdout: str, stderr: str) -> tuple[str, str]:
    limit = output_limit()
    if len(stdout) + len(stderr) <= limit:
        return stdout, stderr
    marker = "\n...[output truncated]\n"
    def tail(value: str, size: int) -> str:
        return value if len(value) <= size else (value[-size:] if size < len(marker) else marker + value[-(size - len(marker)):])
    if not stdout:
        return "", tail(stderr, limit)
    if not stderr:
        return tail(stdout, limit), ""
    stdout_limit = max(1, limit * len(stdout) // (len(stdout) + len(stderr)))
    return tail(stdout, stdout_limit), tail(stderr, limit - stdout_limit)


def audit_target() -> Path:
    directory = Path(setting("HOST_TOOL_AUDIT_DIR"))
    directory.mkdir(parents=True, exist_ok=True)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from log_rotate import rotate_from_environment
    target = directory / "host-bridge.jsonl"
    rotate_from_environment(target)
    return target


def ensure_audit_writable() -> None:
    with audit_target().open("a", encoding="utf-8"):
        pass


def audit(event: dict) -> None:
    with audit_target().open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def require_key(credentials: HTTPAuthorizationCredentials | None) -> None:
    supplied = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else ""
    if not secrets.compare_digest(supplied, setting("HOST_TOOL_API_KEY")):
        raise HTTPException(status_code=401, detail="invalid host bridge API key")


def execute(command: str, shell: str, cwd: str, timeout: float) -> tuple[int, str, str, bool]:
    process = subprocess.Popen([shell, "-lc", command], cwd=cwd, env=os.environ.copy(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        return 124, stdout or "", stderr or f"timed out after {timeout:g} seconds", True


@APP.get("/health")
@APP.get("/health/live")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@APP.get("/health/ready")
async def ready() -> dict[str, str]:
    try:
        if not Path(setting("HOST_TOOL_SHELL")).is_file():
            raise RuntimeError("host shell is unavailable")
        if not Path(setting("HOST_TOOL_CWD")).is_dir():
            raise RuntimeError("host command directory is unavailable")
        ensure_audit_writable()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"status": "ready"}


@APP.post("/run")
async def run_host_command(payload: RunRequest, credentials: HTTPAuthorizationCredentials | None = Depends(BEARER)) -> dict:
    require_key(credentials)
    if payload.timeout_seconds > max_timeout():
        raise HTTPException(status_code=422, detail="timeout exceeds HOST_TOOL_MAX_TIMEOUT_SECONDS")
    started = datetime.now(timezone.utc)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + payload.timeout_seconds
    response: dict = {"exit_code": 125, "stdout": "", "stderr": "internal bridge error"}
    failure: str | None = None
    try:
        shell, cwd = setting("HOST_TOOL_SHELL"), setting("HOST_TOOL_CWD")
        if not Path(shell).is_file() or not os.access(shell, os.X_OK) or not Path(cwd).is_dir():
            raise RuntimeError("host bridge shell or working directory is unavailable")
        ensure_audit_writable()
        await asyncio.wait_for(HOST_LOCK.acquire(), timeout=max(0.001, deadline - loop.time()))
        try:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(payload.command, payload.timeout_seconds)
            code, stdout, stderr, timed_out = await asyncio.to_thread(execute, payload.command, shell, cwd, remaining)
        finally:
            HOST_LOCK.release()
        stdout, stderr = limit_output(stdout, stderr)
        response = {"exit_code": code, "stdout": stdout, "stderr": stderr, "timeout": timed_out}
    except (asyncio.TimeoutError, subprocess.TimeoutExpired):
        response = {"exit_code": 124, "stdout": "", "stderr": f"timed out after {payload.timeout_seconds} seconds", "timeout": True}
    except (OSError, RuntimeError) as error:
        failure = str(error)
        response = {"exit_code": 125, "stdout": "", "stderr": failure, "timeout": False}
    try:
        audit({"at": started.isoformat(), "command": payload.command, "cwd": os.environ.get("HOST_TOOL_CWD", ""), "duration_ms": round((loop.time() - deadline + payload.timeout_seconds) * 1000), "failure": failure, **response})
    except (OSError, RuntimeError) as error:
        response["audit_status"] = "failed"
        response["audit_error"] = str(error)
    else:
        response["audit_status"] = "recorded"
    if failure:
        raise HTTPException(status_code=503, detail="host bridge configuration or runtime failure")
    return response
