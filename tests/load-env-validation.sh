#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

original_mode=$(stat -c %a .env)
restore_mode() { chmod "$original_mode" .env; }
trap restore_mode EXIT
chmod 644 .env
if APPTAINER_BIN=true bash -c 'source scripts/common.sh; load_env'; then
  printf 'load_env accepted an invalid .env permission mode\n' >&2
  exit 1
fi
chmod "$original_mode" .env
