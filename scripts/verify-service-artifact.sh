#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
# shellcheck source=common.sh
source scripts/common.sh
load_env

service=${1:?service name is required}
lock_value() { python3 - "$1" "$2" <<'PY'
import sys, tomllib
from pathlib import Path
print(tomllib.loads(Path('config/apptainer/images.lock').read_text())[sys.argv[1]][sys.argv[2]])
PY
}
verify() { local name=$1 image=$2 source=${3:-} definition=${4:-}; local -a args=(--receipt images/receipts.toml --name "$name" --image "$image"); [[ -z $source ]] || args+=(--source "$source"); [[ -z $definition ]] || args+=(--definition "$definition"); python3 scripts/image-receipts.py verify "${args[@]}"; }

case "$service" in
  llama|embedding) verify llama "$LLAMA_IMAGE" "$(lock_value llama source)" ;;
  searxng) verify searxng "$SEARXNG_IMAGE" "$(lock_value searxng source)" ;;
  docling) verify docling "$DOCLING_IMAGE" "$(lock_value docling source)" ;;
  tool-bridge)
    [[ $TOOL_BRIDGE_ENABLED == true ]] || exit 0
    verify tool "$TOOL_IMAGE" "" "$(lock_value tool definition)"
    ;;
  *) printf 'Unknown artifact-backed service: %s\n' "$service" >&2; exit 2 ;;
esac
