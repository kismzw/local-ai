#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
set -a; source .env; set +a

[[ ${TOOL_BRIDGE_ENABLED:-false} == true ]] || { printf 'Tool bridge is disabled; allowlist test skipped.\n'; exit 0; }
[[ -n ${TOOL_DATA_DIR:-} ]] || { printf 'TOOL_DATA_DIR is required for the allowlist test.\n' >&2; exit 1; }

command='test -d /workspace && test -d /data && grep -Eq "^[^ ]+ /data [^ ]+ ro[, ]" /proc/mounts'
workspace=$(realpath -m "$WORKSPACE_DIR")
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
printf 'Tool bridge allowlist test passed (/workspace read-only, /data read-only, hidden paths masked).\n'
