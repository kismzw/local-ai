from __future__ import annotations

import asyncio
import importlib.util
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.security import HTTPAuthorizationCredentials

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("tool_bridge_app", ROOT / "tool-bridge/app.py")
bridge = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(bridge)


@pytest.fixture(autouse=True)
def settings(monkeypatch, tmp_path):
    monkeypatch.setenv("TOOL_SANDBOX_API_KEY", "secret")
    monkeypatch.setenv("TOOL_MAX_OUTPUT_CHARS", "60")
    monkeypatch.setenv("TOOL_AUDIT_DIR", str(tmp_path))
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    image = tmp_path / "tool.sif"
    image.write_bytes(b"image")
    monkeypatch.setenv("WORKSPACE_DIR", str(workspace))
    monkeypatch.setenv("TOOL_IMAGE", str(image))
    monkeypatch.setenv("APPTAINER_BIN", "true")
    monkeypatch.setenv("TOOL_WRITE_MODE", "read_write")
    monkeypatch.setenv("TOOL_NETWORK_MODE", "unverified")


def test_auth_is_exact_and_constant_time_path_is_used():
    bridge.require_key(HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret"))
    with pytest.raises(bridge.HTTPException):
        bridge.require_key(HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong"))


def test_output_is_bounded_and_marks_truncation():
    stdout, stderr = bridge.limit_output("x" * 100, "y" * 100)
    assert len(stdout) + len(stderr) <= 60
    assert stdout.endswith("x") and stderr.endswith("y")


def test_invalid_output_limit_is_rejected(monkeypatch):
    monkeypatch.setenv("TOOL_MAX_OUTPUT_CHARS", "0")
    with pytest.raises(RuntimeError):
        bridge.output_limit()


def test_hidden_path_must_stay_inside_workspace(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    outside = tmp_path / "secret"
    outside.write_text("secret")
    monkeypatch.setenv("TOOL_HIDDEN_PATHS", str(outside))
    with pytest.raises(RuntimeError):
        bridge.bind_hidden_paths([], workspace)


@pytest.mark.anyio
async def test_workspace_commands_are_serialized(monkeypatch):
    active = 0
    peak = 0

    def fake_run(*_args, **_kwargs):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        time.sleep(0.03)
        active -= 1
        return SimpleNamespace(returncode=0, stdout="ok", stderr="", timed_out=False)

    monkeypatch.setattr(bridge, "run_bounded", fake_run)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret")
    await asyncio.gather(
        bridge.run_tool(bridge.RunRequest(command="true"), credentials),
        bridge.run_tool(bridge.RunRequest(command="true"), credentials),
    )
    assert peak == 1


@pytest.mark.anyio
async def test_sandbox_command_uses_a_dedicated_process_group(monkeypatch):
    invocation = {}

    def fake_run(*_args, **kwargs):
        invocation.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="", timed_out=False)

    monkeypatch.setattr(bridge, "run_bounded", fake_run)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret")
    await bridge.run_tool(bridge.RunRequest(command="true"), credentials)
    assert invocation["start_new_session"] is True


@pytest.mark.anyio
async def test_audit_failure_reports_completed_command(monkeypatch):
    monkeypatch.setattr(bridge, "run_bounded", lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr="", timed_out=False))
    monkeypatch.setattr(bridge, "audit", lambda _event: (_ for _ in ()).throw(OSError("disk full")))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret")
    response = await bridge.run_tool(bridge.RunRequest(command="true", mode="write"), credentials)
    assert response["exit_code"] == 0
    assert response["audit_status"] == "failed"
    assert "disk full" in response["audit_error"]


@pytest.mark.anyio
async def test_write_rejects_unwritable_audit_before_execution(monkeypatch):
    called = False

    def fake_run(*_args, **_kwargs):
        nonlocal called
        called = True
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(bridge, "run_bounded", fake_run)
    monkeypatch.setattr(bridge, "ensure_audit_writable", lambda: (_ for _ in ()).throw(OSError("disk full")))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret")
    with pytest.raises(bridge.HTTPException) as error:
        await bridge.run_tool(bridge.RunRequest(command="true", mode="write"), credentials)
    assert error.value.status_code == 503
    assert not called
