#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

grep -Fq "if [[ \$TOOL_WRITE_MODE == read_write ]]; then" tests/smoke.sh
grep -Fq 'Codex writable workflow skipped (TOOL_WRITE_MODE=read_only).' tests/smoke.sh
