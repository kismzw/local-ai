#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/../scripts/common.sh"
load_env

[[ ${TOOL_BRIDGE_ENABLED:-false} == true ]] || { printf 'Tool bridge is disabled; allowlist test skipped.\n'; exit 0; }
workspace=$(realpath -m "$WORKSPACE_DIR")
probe=$(mktemp "$workspace/.local-ai-allowlist.XXXXXX")
relative_probe=$(realpath --relative-to="$workspace" "$probe")
cleanup() { rm -f "$probe"; }
trap cleanup EXIT

command="test -d /workspace && test -f /workspace/${relative_probe} && grep -Eq '^[^ ]+ /workspace [^ ]+ ro[, ]' /proc/mounts && ! touch /workspace/${relative_probe}.write-denied"
if [[ -n ${TOOL_DATA_DIR:-} ]]; then
  command+=" && test -d /data && grep -Eq '^[^ ]+ /data [^ ]+ ro[, ]' /proc/mounts && ! touch /data/.local-ai-write-denied"
fi
IFS=: read -r -a hidden_paths <<< "${TOOL_HIDDEN_PATHS:-}"
for hidden_path in "${hidden_paths[@]}"; do
  [[ -n "$hidden_path" ]] || continue
  relative=$(realpath --relative-to="$workspace" "$hidden_path")
  command+=" && test ! -s /workspace/${relative}"
done
payload=$(python3 -c 'import json, sys; print(json.dumps({"command": sys.argv[1], "mode": "read"}))' "$command")
response=$(curl -fsS --max-time 35 \
  -H "Authorization: Bearer ${TOOL_SANDBOX_API_KEY}" \
  -H 'Content-Type: application/json' \
  --data "$payload" \
  "http://${TOOL_BRIDGE_BIND}:${TOOL_BRIDGE_PORT}/run")
python3 -c 'import json, sys; reply=json.load(sys.stdin); assert reply["exit_code"] == 0, reply' <<<"$response"
printf 'Tool bridge allowlist test passed (/workspace read-only; optional /data read-only; hidden paths masked).\n'
