from __future__ import annotations

import importlib.util
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("host_bridge", ROOT / "host-bridge/app.py")
host_bridge = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(host_bridge)


def test_host_bridge_runs_with_owner_shell(tmp_path: Path):
    code, stdout, stderr, timed_out = host_bridge.execute("printf host-ok", "/bin/bash", str(tmp_path), 10)
    assert (code, stdout, stderr, timed_out) == (0, "host-ok", "", False)


def test_timeout_terminates_the_host_process_group(tmp_path: Path):
    started = time.monotonic()
    code, _stdout, _stderr, timed_out = host_bridge.execute("sleep 30 & wait", "/bin/bash", str(tmp_path), 0.05)
    assert code == 124
    assert timed_out is True
    assert time.monotonic() - started < 3
