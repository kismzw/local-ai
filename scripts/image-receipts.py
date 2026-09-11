#!/usr/bin/env python3
"""Maintain machine-local SIF integrity receipts for immutable image sources."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path


class ReceiptError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ReceiptError(f"artifact is missing: {path}")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ReceiptError(f"invalid receipt: {exc}") from exc
    if not all(isinstance(name, str) and isinstance(value, dict) for name, value in parsed.items()):
        raise ReceiptError("invalid receipt structure")
    return {name: {key: str(value) for key, value in entry.items()} for name, entry in parsed.items()}


def write(path: Path, receipts: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# Machine-local SIF integrity receipts. Do not commit this file."]
    for name in sorted(receipts):
        lines.extend(("", f"[{name}]"))
        for key in ("source", "artifact_sha256", "definition_sha256", "accepted_at"):
            if key in receipts[name]:
                lines.append(f"{key} = {json.dumps(receipts[name][key])}")
    payload = "\n".join(lines) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(payload)
        temp = Path(stream.name)
    os.chmod(temp, 0o600)
    os.replace(temp, path)


def expected(source: str, image: Path, definition: Path | None) -> dict[str, str]:
    entry = {
        "source": source,
        "artifact_sha256": sha256_file(image),
        "accepted_at": datetime.now(timezone.utc).isoformat(),
    }
    if definition is not None:
        entry["definition_sha256"] = sha256_file(definition)
    return entry


def verify_or_adopt(receipt: Path, name: str, source: str, image: Path, definition: Path | None) -> str:
    receipts = load(receipt)
    actual = expected(source, image, definition)
    recorded = receipts.get(name)
    if recorded is None:
        receipts[name] = actual
        write(receipt, receipts)
        return "adopted"
    for key in ("source", "artifact_sha256"):
        if recorded.get(key) != actual[key]:
            raise ReceiptError(f"receipt mismatch for {name}: {key}")
    if definition is not None and recorded.get("definition_sha256") != actual["definition_sha256"]:
        raise ReceiptError(f"receipt mismatch for {name}: definition_sha256")
    return "verified"


def record(receipt: Path, name: str, source: str, image: Path, definition: Path | None) -> None:
    receipts = load(receipt)
    receipts[name] = expected(source, image, definition)
    write(receipt, receipts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("verify-or-adopt", "record"))
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--definition", type=Path)
    args = parser.parse_args()
    try:
        if args.operation == "verify-or-adopt":
            print(verify_or_adopt(args.receipt, args.name, args.source, args.image, args.definition))
        else:
            record(args.receipt, args.name, args.source, args.image, args.definition)
    except ReceiptError as exc:
        print(f"Receipt error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
