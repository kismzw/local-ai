#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
[[ -f .env ]] || { printf 'Copy .env.example to .env first.\n' >&2; exit 1; }
set -a; source .env; set +a

for command_name in curl sha256sum df; do command -v "$command_name" >/dev/null || { printf 'Missing %s\n' "$command_name" >&2; exit 1; }; done

model_dir=${MODEL_DIR#./}
mkdir -p "$model_dir"

require_space_gib() {
  local needed_gib=$1 available_kib
  available_kib=$(df -Pk "$model_dir" | awk 'NR==2 {print $4}')
  if (( available_kib < needed_gib * 1024 * 1024 )); then
    printf 'Need at least %s GiB free in %s; insufficient disk space.\n' "$needed_gib" "$model_dir" >&2
    exit 1
  fi
}

fetch() {
  local repo=$1 filename=$2 sha=${3:-} target="$model_dir/$2"
  printf '\nRepository: %s\nFile: %s\nTarget: %s\n' "$repo" "$filename" "$target"
  curl --fail --location --continue-at - --retry 5 --retry-delay 3 \
    "https://huggingface.co/${repo}/resolve/main/${filename}?download=true" -o "$target"
  if [[ -n "$sha" ]]; then
    printf '%s  %s\n' "$sha" "$target" | sha256sum --check --status
    printf 'SHA-256 verified for %s.\n' "$filename"
  fi
}

require_space_gib 25
fetch "ggml-org/Qwen3.8-27B-GGUF" "$MODEL_FILE" "31629f53165ab6a7dad8c9847dcfd1fdf55829dac1e6e748f4a68581b0033d34"
require_space_gib 2
fetch "Qwen/Qwen3-Embedding-0.6B-GGUF" "$EMBEDDING_MODEL_FILE"
printf '\nDownloads complete. Primary model checksum was verified.\n'
