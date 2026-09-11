"""Run a subprocess while continuously draining output into bounded tail buffers."""
from __future__ import annotations

import os
import signal
import subprocess
import threading
from collections import deque
from dataclasses import dataclass
from typing import Sequence


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
    process = subprocess.Popen(command, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=start_new_session)
    stdout, stderr = TailBuffer(limit), TailBuffer(limit)

    def drain(stream, buffer: TailBuffer) -> None:
        try:
            while chunk := stream.read(8192):
                buffer.append(chunk)
        except ValueError:
            pass

    readers = [threading.Thread(target=drain, args=(process.stdout, stdout), daemon=True), threading.Thread(target=drain, args=(process.stderr, stderr), daemon=True)]
    for reader in readers:
        reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        if start_new_session:
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            if start_new_session:
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait()
    for stream in (process.stdout, process.stderr):
        stream.close()
    for reader in readers:
        reader.join(timeout=1)
    return Result(process.returncode if not timed_out else 124, stdout.text(), stderr.text(), timed_out)
