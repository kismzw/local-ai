#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
mode=${1:-verify}
case "$mode" in verify|--refresh|--adopt-existing) ;; *) printf 'Usage: %s [--refresh|--adopt-existing]\n' "$0" >&2; exit 2 ;; esac
lock_value() { python3 - "$1" "$2" <<'PY'
import sys, tomllib
from pathlib import Path
print(tomllib.loads(Path('config/apptainer/images.lock').read_text())[sys.argv[1]][sys.argv[2]])
PY
}
receipt=images/receipts.toml
receipt_action() { local action=$1 name=$2 image=$3 source=${4:-} definition=${5:-}; local -a args=(--receipt "$receipt" --name "$name" --image "$image"); [[ -z $source ]] || args+=(--source "$source"); [[ -z $definition ]] || args+=(--definition "$definition"); python3 scripts/image-receipts.py "$action" "${args[@]}"; }
pull_oci() { local name=$1 image=$2 source tmp; source=$(lock_value "$name" source); if [[ $mode == verify && -f $image ]]; then receipt_action verify "$name" "$image" "$source"; return 0; fi; if [[ $mode == --adopt-existing ]]; then [[ -f $image ]] || { printf 'Cannot adopt missing image: %s\n' "$image" >&2; return 1; }; receipt_action adopt "$name" "$image" "$source"; return 0; fi; tmp="${image}.partial"; rm -f "$tmp"; "$APPTAINER_BIN" pull --force "$tmp" "$source"; mv -f "$tmp" "$image"; receipt_action record "$name" "$image" "$source"; }
build_tool() { local image=$1 definition tmp; definition=$(lock_value tool definition); if [[ $mode == verify && -f $image ]]; then receipt_action verify tool "$image" "" "$definition"; return 0; fi; if [[ $mode == --adopt-existing ]]; then [[ -f $image ]] || { printf 'Cannot adopt missing image: %s\n' "$image" >&2; return 1; }; receipt_action adopt tool "$image" "" "$definition"; return 0; fi; tmp="${image}.partial"; rm -f "$tmp"; "$APPTAINER_BIN" build --fakeroot "$tmp" "$definition"; mv -f "$tmp" "$image"; receipt_action record tool "$image" "" "$definition"; }
pull_oci llama "$LLAMA_IMAGE"
if [[ $TOOL_BRIDGE_ENABLED == true ]]; then build_tool "$TOOL_IMAGE"; fi
pull_oci searxng "$SEARXNG_IMAGE"
pull_oci docling "$DOCLING_IMAGE"
printf 'Processed locked SIF images (%s).\n' "$mode"
