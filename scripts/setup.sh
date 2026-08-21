#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

runtime_bin=$(command -v apptainer || command -v singularity || true)
need=()
for command_name in curl python3 openssl; do
  command -v "$command_name" >/dev/null 2>&1 || need+=("$command_name")
done
if [[ -z "$runtime_bin" ]]; then need+=("apptainer-or-singularity"); fi
if ((${#need[@]})); then
  printf 'Missing prerequisite(s): %s\n' "${need[*]}" >&2
  printf 'Apptainer, curl, Python and OpenSSL must be available on PATH.\n' >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  printf 'Created .env from .env.example.\n'
fi

make_secret() { openssl rand -hex 32; }
for secret_name in LLAMA_API_KEY EMBEDDING_API_KEY TOOL_SANDBOX_API_KEY WEBUI_SECRET_KEY; do
  if grep -q "^${secret_name}=CHANGE_ME$" .env; then
    secret_value=$(make_secret)
    sed -i "s/^${secret_name}=CHANGE_ME$/${secret_name}=${secret_value}/" .env
    printf 'Generated %s.\n' "$secret_name"
  fi
done

mkdir -p data/open-webui data/tool-audit data/memory/backups data/workspaces models images run logs benchmarks/results
chmod 700 data/open-webui data/tool-audit data/memory data/memory/backups

printf 'Checking Apptainer GPU passthrough...\n'
"$runtime_bin" exec --nv docker://nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi >/dev/null
printf 'Setup complete. Run ./scripts/pull-images.sh and ./scripts/download-model.sh, then ./scripts/start.sh.\n'
