#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
if rg -n '75% of the configured context|exactly one configured host bind|CORS_ALLOW_ORIGIN=.127\.0\.0\.1:3000' README.md docs config scripts; then
  exit 1
fi
python3 scripts/render-open-webui-adapters.py --check
python3 scripts/config-check.py
uv lock --check --project open-webui-runtime
printf 'Documentation/configuration drift checks passed.\n'
