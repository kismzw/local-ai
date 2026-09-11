from __future__ import annotations

import importlib.util
from pathlib import Path

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
    workspace.mkdir()
    outside = tmp_path / "secret"
    outside.write_text("secret")
    monkeypatch.setenv("TOOL_HIDDEN_PATHS", str(outside))
    with pytest.raises(RuntimeError):
        bridge.bind_hidden_paths([], workspace)
