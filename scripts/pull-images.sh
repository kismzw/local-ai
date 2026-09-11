#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
refresh=${1:-}
[[ -z $refresh || $refresh == --refresh ]] || { printf 'Usage: %s [--refresh]\n' "$0" >&2; exit 2; }
lock_value() { python3 - "$1" "$2" <<'PY'
import sys, tomllib
from pathlib import Path
print(tomllib.loads(Path('config/apptainer/images.lock').read_text())[sys.argv[1]][sys.argv[2]])
PY
}
verify() { local name=$1 image=$2 expected; expected=$(lock_value "$name" sif_sha256); printf '%s  %s\n' "$expected" "$image" | sha256sum --check --status || { printf 'SIF checksum mismatch for %s; use update-lock after intentional upgrade.\n' "$name" >&2; return 1; }; }
pull_oci() { local name=$1 image=$2 source tmp; source=$(lock_value "$name" source); if [[ -f $image && $refresh != --refresh ]]; then verify "$name" "$image"; return; fi; tmp="${image}.partial"; rm -f "$tmp"; "$APPTAINER_BIN" pull --force "$tmp" "$source"; verify "$name" "$tmp"; mv -f "$tmp" "$image"; }
build_tool() { local image=$1 tmp; if [[ -f $image && $refresh != --refresh ]]; then verify tool "$image"; return; fi; tmp="${image}.partial"; rm -f "$tmp"; "$APPTAINER_BIN" build --fakeroot "$tmp" config/apptainer/tool-sandbox.def; verify tool "$tmp"; mv -f "$tmp" "$image"; }
pull_oci llama "$LLAMA_IMAGE"
build_tool "$TOOL_IMAGE"
pull_oci searxng "$SEARXNG_IMAGE"
pull_oci docling "$DOCLING_IMAGE"
printf 'Verified locked SIF images.\n'
