from __future__ import annotations

import importlib.util
import shlex
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("bounded_capture", ROOT / "scripts/bounded_capture.py")
bounded_capture = importlib.util.module_from_spec(spec)
assert spec.loader
sys.modules[spec.name] = bounded_capture
spec.loader.exec_module(bounded_capture)


def test_timeout_terminates_the_entire_process_group(tmp_path: Path):
    child_pid = tmp_path / "child.pid"
    result = bounded_capture.run(
        ["/bin/sh", "-c", f"sleep 30 & echo $! > {shlex.quote(str(child_pid))}; wait"],
        timeout=0.1,
        limit=1000,
        start_new_session=True,
    )
    assert result.timed_out
    pid = int(child_pid.read_text().strip())
    deadline = time.monotonic() + 2
    while Path(f"/proc/{pid}").exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert not Path(f"/proc/{pid}").exists()


def test_drains_final_output_before_closing_pipes():
    result = bounded_capture.run(
        ["/bin/sh", "-c", "printf beginning; printf final-stderr >&2"],
        timeout=2,
        limit=1000,
        start_new_session=True,
    )
    assert result.stdout == "beginning"
    assert result.stderr == "final-stderr"


def test_background_child_cannot_hold_capture_open():
    started = time.monotonic()
    result = bounded_capture.run(
        ["/bin/sh", "-c", "sleep 30 & echo done"],
        timeout=5,
        limit=1000,
        start_new_session=True,
    )
    assert "done" in result.stdout
    assert time.monotonic() - started < 2
