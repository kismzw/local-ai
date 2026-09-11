#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

[[ $(./scripts/service-health-name.sh llama) == llama-server ]]
[[ $(./scripts/service-health-name.sh embedding) == embedding-server ]]
[[ $(./scripts/service-health-name.sh docling-gate) == docling-gate ]]
if ./scripts/service-health-name.sh missing-service >/dev/null 2>&1; then
  printf 'unknown services must be rejected\n' >&2
  exit 1
fi
