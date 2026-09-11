"""Run a subprocess while continuously draining output into bounded tail buffers."""
from __future__ import annotations

import codecs
import os
import select
import signal
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Sequence

DRAIN_GRACE_SECONDS = 0.5
DRAIN_POLL_SECONDS = 0.05


class TailBuffer:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.chunks: deque[str] = deque()
        self.size = 0

    def append(self, chunk: str) -> None:
        self.chunks.append(chunk)
        self.size += len(chunk)
        while self.size > self.limit and self.chunks:
            first = self.chunks[0]
            excess = self.size - self.limit
            if len(first) <= excess:
                self.chunks.popleft()
                self.size -= len(first)
            else:
                self.chunks[0] = first[excess:]
                self.size -= excess

    def text(self) -> str:
        return "".join(self.chunks)


@dataclass
class Result:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


def run(command: Sequence[str], *, timeout: float, limit: int, cwd: str | None = None, env: dict[str, str] | None = None, start_new_session: bool = False) -> Result:
    deadline = time.monotonic() + timeout
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=start_new_session)
    stdout, stderr = TailBuffer(limit), TailBuffer(limit)
    stop_readers = threading.Event()

    def drain(stream, buffer: TailBuffer) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            descriptor = stream.fileno()
            while not stop_readers.is_set():
                ready, _, _ = select.select([descriptor], [], [], DRAIN_POLL_SECONDS)
                if not ready:
                    continue
                chunk = os.read(descriptor, 8192)
                if not chunk:
                    buffer.append(decoder.decode(b"", final=True))
                    return
                buffer.append(decoder.decode(chunk))
            buffer.append(decoder.decode(b"", final=True))
        except (OSError, ValueError):
            # The parent closes a lingering descriptor only after this reader stops.
            return

    readers = [threading.Thread(target=drain, args=(process.stdout, stdout), daemon=True), threading.Thread(target=drain, args=(process.stderr, stderr), daemon=True)]
    for reader in readers:
        reader.start()

    def signal_process_group(signal_number: int) -> None:
        try:
            os.killpg(process.pid, signal_number)
        except ProcessLookupError:
            # The command and all of its children already exited.
            pass

    timed_out = False
    try:
        process.wait(timeout=max(0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        timed_out = True
        if start_new_session:
            signal_process_group(signal.SIGTERM)
        else:
            process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            if start_new_session:
                signal_process_group(signal.SIGKILL)
            else:
                process.kill()
            process.wait()
        if start_new_session:
            # The group leader may exit after SIGTERM while a child remains.  Kill
            # any survivor before releasing the caller's serialization lock.
            signal_process_group(signal.SIGKILL)
    # A normally terminating command reaches EOF immediately, preserving its final
    # diagnostics.  A background or detached child can retain these pipe FDs after
    # its direct parent exits, so never let draining them hold a bridge request open.
    drain_deadline = min(deadline, time.monotonic() + DRAIN_GRACE_SECONDS)
    for reader in readers:
        reader.join(timeout=max(0, drain_deadline - time.monotonic()))
    if any(reader.is_alive() for reader in readers):
        stop_readers.set()
    for reader in readers:
        reader.join(timeout=DRAIN_GRACE_SECONDS)
    for stream, reader in zip((process.stdout, process.stderr), readers):
        if not reader.is_alive():
            stream.close()
    return Result(process.returncode if not timed_out else 124, stdout.text(), stderr.text(), timed_out)
