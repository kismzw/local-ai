#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

runtime_bin=${APPTAINER_BIN:-}
if [[ -z $runtime_bin ]]; then runtime_bin=$(command -v apptainer || command -v singularity || true); fi
uv_bin=${UV_BIN:-"$HOME/.local/bin/uv"}
need=()
for command_name in curl python3 openssl; do
  command -v "$command_name" >/dev/null 2>&1 || need+=("$command_name")
done
if [[ -z "$runtime_bin" ]]; then need+=("apptainer-or-singularity"); fi
[[ -x $uv_bin ]] || need+=("uv (run scripts/install-uv.sh first)")
if ((${#need[@]})); then
  printf 'Missing prerequisite(s): %s\n' "${need[*]}" >&2
  printf 'Apptainer, curl, Python and OpenSSL must be available on PATH.\n' >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  printf 'Created .env from .env.example.\n'
fi
chmod 600 .env

ensure_variable() {
  local name=$1 value=$2
  grep -q "^${name}=" .env || printf '%s=%s\n' "$name" "$value" >> .env
}

ensure_variable SEARXNG_IMAGE ./images/searxng.sif
ensure_variable DOCLING_IMAGE ./images/docling-serve-cu128.sif
ensure_variable SEARXNG_PORT 8082
ensure_variable DOCLING_GATE_PORT 5001
ensure_variable DOCLING_PORT 5002
ensure_variable SEARXNG_CACHE_DIR ./data/searxng/cache
ensure_variable DOCLING_ARTIFACTS_DIR ./data/docling/artifacts
ensure_variable DOCLING_AUDIT_DIR ./data/docling/audit
ensure_variable SEARXNG_SECRET CHANGE_ME
ensure_variable DOCLING_GATE_API_KEY CHANGE_ME
ensure_variable WEB_SEARCH_ENABLED true
ensure_variable WEB_SEARCH_RESULT_COUNT 5
ensure_variable WEB_SEARCH_CONCURRENT_REQUESTS 1
ensure_variable WEB_LOADER_CONCURRENT_REQUESTS 2
ensure_variable WEB_LOADER_TIMEOUT_SECONDS 20
ensure_variable WEB_FETCH_MAX_CONTENT_LENGTH 40000
ensure_variable DOCLING_GATE_IDLE_SECONDS 10
ensure_variable DOCLING_GATE_POLL_SECONDS 5
ensure_variable DOCLING_GATE_MAX_WAIT_SECONDS 600
ensure_variable DOCLING_GATE_MAX_RETRIES 3
ensure_variable DOCLING_GATE_MAX_UNKNOWN_POLLS 3
ensure_variable DOCLING_MAX_SYNC_WAIT_SECONDS 600
ensure_variable LOG_MAX_BYTES 10485760
ensure_variable LOG_ROTATION_COUNT 5
ensure_variable HOST_TOOL_ENABLED false
ensure_variable HOST_TOOL_BIND 127.0.0.1
ensure_variable HOST_TOOL_PORT 8091
ensure_variable HOST_TOOL_AUDIT_DIR ./data/host-tool-audit
ensure_variable HOST_TOOL_MAX_OUTPUT_CHARS 12000
ensure_variable HOST_TOOL_MAX_TIMEOUT_SECONDS 300
ensure_variable HOST_TOOL_CWD "$HOME"
ensure_variable HOST_TOOL_SHELL /bin/bash

make_secret() { openssl rand -hex 32; }
for secret_name in LLAMA_API_KEY EMBEDDING_API_KEY TOOL_SANDBOX_API_KEY HOST_TOOL_API_KEY SEARXNG_SECRET DOCLING_GATE_API_KEY WEBUI_SECRET_KEY; do
  if grep -q "^${secret_name}=CHANGE_ME$" .env; then
    secret_value=$(make_secret)
    sed -i "s/^${secret_name}=CHANGE_ME$/${secret_name}=${secret_value}/" .env
    printf 'Generated %s.\n' "$secret_name"
  fi
done

mkdir -p data/open-webui data/tool-audit data/host-tool-audit data/searxng/cache data/docling/artifacts data/docling/audit data/memory/backups data/workspaces models images run logs benchmarks/results
chmod 700 data/open-webui data/tool-audit data/host-tool-audit data/searxng data/searxng/cache data/docling data/docling/artifacts data/docling/audit data/memory data/memory/backups

printf 'Checking Apptainer GPU passthrough...\n'
gpu_probe=$(python3 -c 'import tomllib; print(tomllib.load(open("config/apptainer/images.lock", "rb"))["gpu_probe"]["source"])')
"$runtime_bin" exec --nv "$gpu_probe" nvidia-smi >/dev/null
python3 scripts/config-check.py
"$uv_bin" sync --project docling-gate --locked
"$uv_bin" sync --project tool-bridge --locked
"$uv_bin" sync --project open-webui-runtime --locked
./scripts/systemd.sh install
printf 'Setup complete. Run ./scripts/pull-images.sh and ./scripts/download-model.sh, then ./scripts/start.sh.\n'
