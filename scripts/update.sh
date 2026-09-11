#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
printf 'This refreshes only OCI SIFs pinned in images.lock.\n'
./scripts/stop.sh
./scripts/pull-images.sh --refresh
./scripts/start.sh
