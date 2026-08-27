#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
root_dir=$root_dir
preflight_only=${1:-}
failed=0
check() { local label=$1; shift; if "$@" >/dev/null 2>&1; then printf '[ok] %s\n' "$label"; else printf '[!!] %s\n' "$label" >&2; failed=1; fi; }

[[ -f .env ]] && load_env || true
check 'NVIDIA driver / nvidia-smi' nvidia-smi
check 'Apptainer or Singularity' bash -c 'command -v apptainer || command -v singularity'
check '.env exists' test -f .env
if [[ -f .env ]]; then
  check 'Apptainer GPU passthrough' "$APPTAINER_BIN" exec --nv docker://nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
  check 'llama.cpp SIF image' test -f "$LLAMA_IMAGE"
  check 'tool SIF image' test -f "$TOOL_IMAGE"
  check 'SearXNG SIF image' test -f "$SEARXNG_IMAGE"
  check 'Docling CUDA SIF image' test -f "$DOCLING_IMAGE"
fi
check 'model directory exists' test -d models
if [[ -f .env ]]; then
  check "primary model exists (${MODEL_FILE})" test -f "${MODEL_DIR}/${MODEL_FILE}"
  check "embedding model exists (${EMBEDDING_MODEL_FILE})" test -f "${MODEL_DIR}/${EMBEDDING_MODEL_FILE}"
fi
check 'Open WebUI port is free or owned by this stack' bash -c '! ss -ltn "sport = :3000" 2>/dev/null | grep -q LISTEN || test -f run/open-webui.pid'
check 'llama.cpp port is free or owned by this stack' bash -c '! ss -ltn "sport = :8080" 2>/dev/null | grep -q LISTEN || test -f run/llama-server.pid'
check 'SearXNG port is free or owned by this stack' bash -c "! ss -ltn 'sport = :${SEARXNG_PORT:-8082}' 2>/dev/null | grep -q LISTEN || test -f run/searxng.pid"
check 'Docling gate port is free or owned by this stack' bash -c "! ss -ltn 'sport = :${DOCLING_GATE_PORT:-5001}' 2>/dev/null | grep -q LISTEN || test -f run/docling-gate.pid"
printf '[info] Disk: '; df -h . | awk 'NR==2 {print $4 " available"}'
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null || true

if [[ "$preflight_only" == '--preflight' ]]; then exit "$failed"; fi
if pid_running run/llama-server.pid; then
  check 'GPU visible inside inference SIF' "$APPTAINER_BIN" exec --nv "$LLAMA_IMAGE" nvidia-smi
  check 'llama health endpoint' curl -fsS "http://${LLAMA_SERVER_BIND:-127.0.0.1}:${LLAMA_SERVER_PORT:-8080}/health"
  check 'OpenAI /v1/models endpoint' bash -c "curl -fsS -H 'Authorization: Bearer ${LLAMA_API_KEY}' http://${LLAMA_SERVER_BIND:-127.0.0.1}:${LLAMA_SERVER_PORT:-8080}/v1/models | grep -q qwen3.8-27b"
  check 'native Open WebUI health endpoint' curl -fsS "http://${OPEN_WEBUI_BIND:-127.0.0.1}:${OPEN_WEBUI_PORT:-3000}/health"
  check 'restricted tool filesystem and network isolation' ./tests/tool-isolation.sh
fi
if pid_running run/tool-bridge.pid; then
  check 'tool bridge explicit workspace/data allowlist' ./tests/tool-bridge-allowlist.sh
  check 'Codex tool bridge workflow' ./tests/tool-bridge-codex.sh
fi
if pid_running run/searxng.pid; then
  check 'SearXNG health endpoint' curl -fsS "http://127.0.0.1:${SEARXNG_PORT}/healthz"
  check 'SearXNG JSON search' bash -c "curl -fsS 'http://127.0.0.1:${SEARXNG_PORT}/search?q=Open+WebUI&format=json' | grep -q '\"results\"'"
fi
if pid_running run/open-webui.pid; then
  check 'web fetch blocks local/private/metadata targets' ./tests/web-fetch-isolation.sh
fi
if pid_running run/docling-gate.pid; then
  check 'Docling gate health endpoint' curl -fsS "http://127.0.0.1:${DOCLING_GATE_PORT}/health"
fi
if pid_running run/docling.pid; then
  check 'GPU visible inside Docling SIF' "$APPTAINER_BIN" exec --nv "$DOCLING_IMAGE" nvidia-smi
  check 'Docling backend health endpoint' curl -fsS "http://127.0.0.1:${DOCLING_PORT}/health"
fi
exit "$failed"
