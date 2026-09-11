#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

load_env() {
  local rendered
  rendered=$(python3 "$root_dir/scripts/config-check.py" --shell) || return $?
  eval "$rendered"
  if [[ -z ${APPTAINER_BIN:-} ]]; then
    if command -v apptainer >/dev/null 2>&1; then APPTAINER_BIN=apptainer
    elif command -v singularity >/dev/null 2>&1; then APPTAINER_BIN=singularity
    else printf 'Neither apptainer nor singularity is available on PATH.\n' >&2; exit 1
    fi
  fi
  command -v "$APPTAINER_BIN" >/dev/null 2>&1 || { printf 'Configured runtime is unavailable: %s\n' "$APPTAINER_BIN" >&2; exit 1; }
}

absolute_path() {
  realpath -m "$1"
}

ensure_dirs() {
  mkdir -p "$MODEL_DIR" "$OPEN_WEBUI_DATA_DIR" "$SEARXNG_CACHE_DIR" "$DOCLING_ARTIFACTS_DIR" "$DOCLING_AUDIT_DIR" images run logs benchmarks/results data/memory/backups
  chmod 700 "$OPEN_WEBUI_DATA_DIR" "$SEARXNG_CACHE_DIR" "$DOCLING_ARTIFACTS_DIR" "$DOCLING_AUDIT_DIR" data/memory data/memory/backups
  if [[ ${TOOL_BRIDGE_ENABLED:-false} == true ]]; then
    mkdir -p "$TOOL_AUDIT_DIR" "$WORKSPACE_DIR"
    chmod 700 "$TOOL_AUDIT_DIR"
  fi
}

require_file() {
  [[ -f $1 ]] || { printf 'Required file missing: %s\n' "$1" >&2; exit 1; }
}
