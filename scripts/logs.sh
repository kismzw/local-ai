#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
service=${1:-}
if [[ -n "$service" ]]; then exec tail -n 200 -f "logs/${service}.log"; fi
exec tail -n 200 -f logs/*.log
