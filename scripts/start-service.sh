#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
service=${1:?service name is required}
health_service=$(./scripts/service-health-name.sh "$service")
./scripts/systemd.sh prepare
systemctl --user start "local-ai-${service}.service"
./scripts/health-check.sh "$health_service"
