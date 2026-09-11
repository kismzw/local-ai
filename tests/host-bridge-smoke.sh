#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=../scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../scripts/common.sh"
load_env
[[ $HOST_TOOL_ENABLED == true ]] || exit 0
response=$(curl -fsS --max-time 20 -X POST "http://${HOST_TOOL_BIND}:${HOST_TOOL_PORT}/run" \
  -H "Authorization: Bearer $HOST_TOOL_API_KEY" -H 'Content-Type: application/json' \
  --data '{"command":"printf HOST_BRIDGE_OK","timeout_seconds":10}')
grep -Fq 'HOST_BRIDGE_OK' <<<"$response"
grep -Fq '"audit_status": "recorded"' <<<"$response"
