from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.security import HTTPAuthorizationCredentials
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("host_bridge", ROOT / "host-bridge/app.py")
host_bridge = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(host_bridge)


@pytest.fixture(autouse=True)
def settings(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOST_TOOL_API_KEY", "host-secret")
    monkeypatch.setenv("HOST_TOOL_AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("HOST_TOOL_CWD", str(tmp_path))
    monkeypatch.setenv("HOST_TOOL_SHELL", "/bin/bash")
    monkeypatch.setenv("HOST_TOOL_MAX_OUTPUT_CHARS", "1000")
    monkeypatch.setenv("HOST_TOOL_MAX_TIMEOUT_SECONDS", "300")
    monkeypatch.setenv("LOG_MAX_BYTES", "100000")
    monkeypatch.setenv("LOG_ROTATION_COUNT", "2")


def test_host_bridge_runs_with_owner_shell(tmp_path: Path):
    code, stdout, stderr, timed_out = host_bridge.execute("printf host-ok", "/bin/bash", str(tmp_path), 10)
    assert (code, stdout, stderr, timed_out) == (0, "host-ok", "", False)


def test_timeout_terminates_the_host_process_group(tmp_path: Path):
    started = time.monotonic()
    code, _stdout, _stderr, timed_out = host_bridge.execute("sleep 30 & wait", "/bin/bash", str(tmp_path), 0.05)
    assert code == 124
    assert timed_out is True
    assert time.monotonic() - started < 3


def test_output_is_drained_into_a_bounded_tail_buffer(tmp_path: Path):
    code, stdout, stderr, timed_out = host_bridge.execute("python3 -c 'print(\"x\" * 1000000)'", "/bin/bash", str(tmp_path), 10)
    assert code == 0 and not timed_out and not stderr
    assert len(stdout) <= 1000
    assert stdout.endswith("x\n")


def test_systemd_session_environment_is_refreshed(monkeypatch):
    monkeypatch.setattr(host_bridge.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="SSH_AUTH_SOCK=/run/agent\nIGNORED=value\nDISPLAY=:1\n"))
    assert host_bridge.systemd_session_environment() == {"SSH_AUTH_SOCK": "/run/agent", "DISPLAY": ":1"}


def test_session_environment_delay_counts_against_timeout(monkeypatch, tmp_path: Path):
    invoked = False

    def delayed_environment(*, timeout: float):
        assert timeout <= 0.01
        time.sleep(0.02)
        return {}

    def must_not_run(*_args, **_kwargs):
        nonlocal invoked
        invoked = True
        pytest.fail("command started after its timeout budget was exhausted")

    monkeypatch.setattr(host_bridge, "systemd_session_environment", delayed_environment)
    monkeypatch.setattr(host_bridge, "run_bounded", must_not_run)
    code, stdout, stderr, timed_out = host_bridge.execute("true", "/bin/bash", str(tmp_path), 0.01)
    assert (code, stdout, timed_out) == (124, "", True)
    assert "timed out" in stderr
    assert not invoked


def test_audit_permissions_are_owner_only(tmp_path: Path):
    target = host_bridge.audit_target()
    assert target.parent.stat().st_mode & 0o777 == 0o700
    assert target.stat().st_mode & 0o777 == 0o600


@pytest.mark.anyio
async def test_authenticated_command_uses_configured_cwd_and_records_both_audit_phases(tmp_path: Path):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="host-secret")
    response = await host_bridge.run_host_command(host_bridge.RunRequest(command="pwd"), credentials)
    assert response["exit_code"] == 0
    assert response["stdout"].strip() == str(tmp_path)
    events = [json.loads(line) for line in (tmp_path / "audit" / "host-bridge.jsonl").read_text().splitlines()]
    assert [event["phase"] for event in events] == ["start", "complete"]


@pytest.mark.anyio
async def test_invalid_key_and_audit_failure_do_not_execute(monkeypatch):
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong")
    with pytest.raises(host_bridge.HTTPException) as error:
        await host_bridge.run_host_command(host_bridge.RunRequest(command="true"), credentials)
    assert error.value.status_code == 401
    monkeypatch.setattr(host_bridge, "audit", lambda _event: (_ for _ in ()).throw(OSError("disk full")))
    monkeypatch.setattr(host_bridge, "execute", lambda *_args: pytest.fail("command executed without start audit"))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="host-secret")
    with pytest.raises(host_bridge.HTTPException) as error:
        await host_bridge.run_host_command(host_bridge.RunRequest(command="true"), credentials)
    assert error.value.status_code == 503


@pytest.mark.anyio
async def test_configured_timeout_limit_is_enforced(monkeypatch):
    monkeypatch.setenv("HOST_TOOL_MAX_TIMEOUT_SECONDS", "2")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="host-secret")
    with pytest.raises(host_bridge.HTTPException) as error:
        await host_bridge.run_host_command(host_bridge.RunRequest(command="true", timeout_seconds=3), credentials)
    assert error.value.status_code == 422


@pytest.mark.anyio
async def test_queue_wait_counts_against_the_command_timeout():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="host-secret")
    await host_bridge.HOST_LOCK.acquire()
    try:
        response = await host_bridge.run_host_command(host_bridge.RunRequest(command="true", timeout_seconds=1), credentials)
    finally:
        host_bridge.HOST_LOCK.release()
    assert response["exit_code"] == 124
    assert response["timeout"] is True


@pytest.mark.anyio
async def test_readiness_reports_audit_io_failure_as_unavailable(monkeypatch):
    monkeypatch.setattr(host_bridge, "ensure_audit_writable", lambda: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(host_bridge.HTTPException) as error:
        await host_bridge.ready()
    assert error.value.status_code == 503
