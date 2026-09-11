#!/usr/bin/env python3
"""Record a deliberately selected immutable OCI source and its SIF checksum."""
from __future__ import annotations
import argparse
import hashlib
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
lock = root / "config/apptainer/images.lock"
parser = argparse.ArgumentParser()
parser.add_argument("name", choices=("llama", "tool", "searxng", "docling"))
parser.add_argument("source", help="digest-pinned docker://...@sha256:<digest>")
parser.add_argument("sif", type=Path, help="SIF freshly built/pulled from that source")
args = parser.parse_args()
if not re.fullmatch(r"docker://[^@]+@sha256:[0-9a-f]{64}", args.source):
    parser.error("source must be a digest-pinned docker reference")
if not args.sif.is_file():
    parser.error("sif must exist")
with args.sif.open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
source_pattern = rf"(\[{args.name}\]\nsource = )\"[^\"]+\"(\nsif_sha256 = )\"[^\"]+\""
updated, count = re.subn(source_pattern, rf'\g<1>"{args.source}"\g<2>"{digest}"', lock.read_text())
if count != 1:
    raise SystemExit("lock section not found")
lock.write_text(updated)
print(f"Updated {args.name}; review and commit {lock.relative_to(root)}")
