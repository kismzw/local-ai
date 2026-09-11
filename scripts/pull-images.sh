#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=common.sh
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
receipt=images/receipts.toml
verify() { local name=$1 image=$2 source=$3 definition=${4:-}; local -a args=(--receipt "$receipt" --name "$name" --source "$source" --image "$image"); [[ -z $definition ]] || args+=(--definition "$definition"); python3 scripts/image-receipts.py verify-or-adopt "${args[@]}"; }
record() { local name=$1 image=$2 source=$3 definition=${4:-}; local -a args=(--receipt "$receipt" --name "$name" --source "$source" --image "$image"); [[ -z $definition ]] || args+=(--definition "$definition"); python3 scripts/image-receipts.py record "${args[@]}"; }
pull_oci() { local name=$1 image=$2 source tmp; source=$(lock_value "$name" source); if [[ -f $image ]]; then verify "$name" "$image" "$source"; if [[ $refresh != --refresh ]]; then return 0; fi; fi; tmp="${image}.partial"; rm -f "$tmp"; "$APPTAINER_BIN" pull --force "$tmp" "$source"; mv -f "$tmp" "$image"; record "$name" "$image" "$source"; }
build_tool() { local image=$1 source definition tmp; source=$(lock_value tool source); definition=$(lock_value tool definition); if [[ -f $image ]]; then verify tool "$image" "$source" "$definition"; if [[ $refresh != --refresh ]]; then return 0; fi; fi; tmp="${image}.partial"; rm -f "$tmp"; "$APPTAINER_BIN" build --fakeroot "$tmp" "$definition"; mv -f "$tmp" "$image"; record tool "$image" "$source" "$definition"; }
pull_oci llama "$LLAMA_IMAGE"
build_tool "$TOOL_IMAGE"
pull_oci searxng "$SEARXNG_IMAGE"
pull_oci docling "$DOCLING_IMAGE"
printf 'Verified locked SIF images.\n'
