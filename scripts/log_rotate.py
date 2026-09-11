#!/usr/bin/env python3
"""Small user-space rotation helper for JSONL audit logs."""
from __future__ import annotations

import os
from pathlib import Path


def rotate(path: Path, maximum: int, count: int) -> None:
    if not path.exists() or path.stat().st_size < maximum:
        return
    oldest = path.with_name(f"{path.name}.{count}")
    oldest.unlink(missing_ok=True)
    for index in range(count - 1, 0, -1):
        previous = path.with_name(f"{path.name}.{index}")
        if previous.exists():
            previous.replace(path.with_name(f"{path.name}.{index + 1}"))
    path.replace(path.with_name(f"{path.name}.1"))


def rotate_from_environment(path: Path) -> None:
    rotate(path, int(os.environ.get("LOG_MAX_BYTES", "10485760")), int(os.environ.get("LOG_ROTATION_COUNT", "5")))
