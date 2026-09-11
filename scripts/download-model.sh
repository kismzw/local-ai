#!/usr/bin/env bash
set -Eeuo pipefail

# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
for command_name in curl sha256sum df; do command -v "$command_name" >/dev/null || { printf 'Missing %s\n' "$command_name" >&2; exit 1; }; done

model_field() { python3 - "$1" "$2" <<'PY'
import sys, tomllib
from pathlib import Path
print(tomllib.loads(Path('config/models.toml').read_text())[sys.argv[1]][sys.argv[2]])
PY
}

require_space_gib() {
  local needed_gib=$1 available_kib
  available_kib=$(df -Pk "$MODEL_DIR" | awk 'NR==2 {print $4}')
  if (( available_kib < needed_gib * 1024 * 1024 )); then
    printf 'Need at least %s GiB free in %s; insufficient disk space.\n' "$needed_gib" "$MODEL_DIR" >&2
    exit 1
  fi
}

fetch() {
  local role=$1 repo filename sha target partial
  repo=$(model_field "$role" repo)
  filename=$(model_field "$role" filename)
  sha=$(model_field "$role" sha256)
  [[ $sha =~ ^[0-9a-f]{64}$ ]] || { printf 'Missing SHA-256 for %s in config/models.toml.\n' "$role" >&2; exit 1; }
  target="$MODEL_DIR/$filename"
  partial="${target}.partial"
  printf '\nRepository: %s\nFile: %s\nTarget: %s\n' "$repo" "$filename" "$target"
  curl --fail --location --continue-at - --retry 5 --retry-delay 3 \
    "https://huggingface.co/${repo}/resolve/main/${filename}?download=true" -o "$partial"
  printf '%s  %s\n' "$sha" "$partial" | sha256sum --check --status
  mv -f "$partial" "$target"
  printf 'SHA-256 verified for %s.\n' "$filename"
}

require_space_gib 25
fetch chat
require_space_gib 2
fetch embedding
printf '\nDownloads complete and both checksums were verified.\n'
