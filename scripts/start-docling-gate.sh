#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
uv_bin=${UV_BIN:-"$HOME/.local/bin/uv"}
[[ -x "$uv_bin" ]] || { printf 'uv is not installed. Run ./scripts/install-uv.sh.\n' >&2; exit 1; }

audit_dir="$(absolute_path "$DOCLING_AUDIT_DIR")"
start_background docling-gate env \
  DOCLING_GATE_API_KEY="$DOCLING_GATE_API_KEY" \
  DOCLING_BACKEND_URL="http://127.0.0.1:${DOCLING_PORT}" \
  LLAMA_METRICS_URL="http://${LLAMA_SERVER_BIND}:${LLAMA_SERVER_PORT}/metrics" \
  LLAMA_SLOTS_URL="http://${LLAMA_SERVER_BIND}:${LLAMA_SERVER_PORT}/slots" \
  LLAMA_METRICS_API_KEY="$LLAMA_API_KEY" \
  DOCLING_GATE_IDLE_SECONDS="$DOCLING_GATE_IDLE_SECONDS" \
  DOCLING_GATE_POLL_SECONDS="$DOCLING_GATE_POLL_SECONDS" \
  DOCLING_GATE_MAX_WAIT_SECONDS="$DOCLING_GATE_MAX_WAIT_SECONDS" \
  DOCLING_GATE_MAX_RETRIES="$DOCLING_GATE_MAX_RETRIES" \
  DOCLING_AUDIT_DIR="$audit_dir" \
  UV_CACHE_DIR="$(absolute_path .uv/cache)" \
  "$uv_bin" run --project docling-gate --python 3.11 uvicorn --app-dir docling-gate app:APP --host 127.0.0.1 --port "$DOCLING_GATE_PORT"
