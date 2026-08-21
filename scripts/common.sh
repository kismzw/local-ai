#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

load_env() {
  [[ -f .env ]] || { printf 'Missing .env; copy .env.example first.\n' >&2; exit 1; }
  set -a; source .env; set +a
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
  mkdir -p "$MODEL_DIR" "$OPEN_WEBUI_DATA_DIR" "$TOOL_AUDIT_DIR" "$WORKSPACE_DIR" images run logs benchmarks/results data/memory/backups
  chmod 700 "$OPEN_WEBUI_DATA_DIR" "$TOOL_AUDIT_DIR" data/memory data/memory/backups
}

require_file() {
  [[ -f $1 ]] || { printf 'Required file missing: %s\n' "$1" >&2; exit 1; }
}

pid_running() {
  [[ -f $1 ]] && kill -0 "$(<"$1")" 2>/dev/null
}

start_background() {
  local name=$1; shift
  local pidfile="run/${name}.pid" logfile="logs/${name}.log"
  if pid_running "$pidfile"; then printf '%s already running (pid %s).\n' "$name" "$(<"$pidfile")"; return; fi
  rm -f "$pidfile"
  # Apptainer can tie container lifecycle to its parent process group; detach
  # into a new session in addition to ignoring SIGHUP.
  nohup setsid "$@" >>"$logfile" 2>&1 &
  printf '%s\n' "$!" > "$pidfile"
  printf 'Started %s (pid %s); log: %s\n' "$name" "$!" "$logfile"
}
