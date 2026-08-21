#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
printf 'This refreshes the OCI SIFs and the pinned native Open WebUI package. Review .env first.\n'
./scripts/stop.sh
FORCE_PULL=true ./scripts/pull-images.sh
./scripts/start.sh
