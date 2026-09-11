#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
preflight_only=${1:-}
failed=0
check() { local label=$1; shift; if "$@" >/dev/null 2>&1; then printf '[ok] %s\n' "$label"; else printf '[!!] %s\n' "$label" >&2; failed=1; fi; }
load_env
check 'configuration' python3 scripts/config-check.py
check 'NVIDIA driver / nvidia-smi' nvidia-smi
check 'configured Apptainer/Singularity runtime' command -v "$APPTAINER_BIN"
check 'llama.cpp SIF image' test -f "$LLAMA_IMAGE"
check 'SearXNG SIF image' test -f "$SEARXNG_IMAGE"
check 'Docling CUDA SIF image' test -f "$DOCLING_IMAGE"
if [[ $TOOL_BRIDGE_ENABLED == true ]]; then check 'tool SIF image' test -f "$TOOL_IMAGE"; fi
receipt=images/receipts.toml
receipt_check() { local name=$1 image=$2 source=${3:-} definition=${4:-}; local -a args=(--receipt "$receipt" --name "$name" --image "$image"); [[ -z $source ]] || args+=(--source "$source"); [[ -z $definition ]] || args+=(--definition "$definition"); check "$name SIF receipt" python3 scripts/image-receipts.py verify "${args[@]}"; }
lock_value() { python3 - "$1" "$2" <<'PY'
import sys, tomllib
from pathlib import Path
print(tomllib.loads(Path('config/apptainer/images.lock').read_text())[sys.argv[1]][sys.argv[2]])
PY
}
if [[ $preflight_only != --preflight ]]; then
  receipt_check llama "$LLAMA_IMAGE" "$(lock_value llama source)"
  receipt_check searxng "$SEARXNG_IMAGE" "$(lock_value searxng source)"
  receipt_check docling "$DOCLING_IMAGE" "$(lock_value docling source)"
  if [[ $TOOL_BRIDGE_ENABLED == true ]]; then receipt_check tool "$TOOL_IMAGE" "" "$(lock_value tool definition)"; fi
  model_sha() { python3 - "$1" <<'PY'
import sys, tomllib
print(tomllib.load(open("config/models.toml", "rb"))[sys.argv[1]]["sha256"])
PY
}
  if printf '%s  %s\n' "$(model_sha chat)" "${MODEL_DIR}/${MODEL_FILE}" | sha256sum --check --status >/dev/null; then printf '[ok] primary model SHA-256 (%s)\n' "$MODEL_FILE"; else printf '[!!] primary model SHA-256 (%s)\n' "$MODEL_FILE" >&2; failed=1; fi
  if printf '%s  %s\n' "$(model_sha embedding)" "${MODEL_DIR}/${EMBEDDING_MODEL_FILE}" | sha256sum --check --status >/dev/null; then printf '[ok] embedding model SHA-256 (%s)\n' "$EMBEDDING_MODEL_FILE"; else printf '[!!] embedding model SHA-256 (%s)\n' "$EMBEDDING_MODEL_FILE" >&2; failed=1; fi
fi
for item in "open-webui:$OPEN_WEBUI_PORT" "llama:$LLAMA_SERVER_PORT" "embedding:$EMBEDDING_SERVER_PORT" "searxng:$SEARXNG_PORT" "docling-gate:$DOCLING_GATE_PORT" "docling:$DOCLING_PORT"; do
  name=${item%%:*}; port=${item##*:}
  if ss -ltn "sport = :$port" 2>/dev/null | grep -q LISTEN && ! systemctl --user is-active --quiet "local-ai-${name}.service"; then printf '[!!] port %s is occupied by a non-Local-AI listener\n' "$port" >&2; failed=1; else printf '[ok] port %s is available or managed\n' "$port"; fi
done
if [[ $TOOL_BRIDGE_ENABLED == true ]]; then
  if ss -ltn "sport = :$TOOL_BRIDGE_PORT" 2>/dev/null | grep -q LISTEN && ! systemctl --user is-active --quiet local-ai-tool-bridge.service; then printf '[!!] tool bridge port is occupied\n' >&2; failed=1; else printf '[ok] tool bridge port is available or managed\n'; fi
fi
if [[ $HOST_TOOL_ENABLED == true ]]; then
  if ss -ltn "sport = :$HOST_TOOL_PORT" 2>/dev/null | grep -q LISTEN && ! systemctl --user is-active --quiet local-ai-host-bridge.service; then printf '[!!] host bridge port is occupied\n' >&2; failed=1; else printf '[ok] host bridge port is available or managed\n'; fi
fi
printf '[info] Disk: '; df -h . | awk 'NR==2 {print $4 " available"}'
[[ $preflight_only == --preflight ]] && exit "$failed"
for service in llama-server embedding-server docling docling-gate searxng open-webui; do
  unit=${service/llama-server/llama}; unit=${unit/embedding-server/embedding}
  if systemctl --user is-active --quiet "local-ai-${unit}.service"; then check "$service readiness" ./scripts/health-check.sh "$service"; fi
done
if [[ $TOOL_BRIDGE_ENABLED == true && $(systemctl --user is-active local-ai-tool-bridge.service 2>/dev/null || true) == active ]]; then check 'tool bridge allowlist' ./tests/tool-bridge-allowlist.sh; fi
if [[ $HOST_TOOL_ENABLED == true && $(systemctl --user is-active local-ai-host-bridge.service 2>/dev/null || true) == active ]]; then check 'host bridge readiness' ./scripts/health-check.sh host-bridge; fi
exit "$failed"
