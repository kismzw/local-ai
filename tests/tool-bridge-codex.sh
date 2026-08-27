#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
set -a; source .env; set +a

[[ ${TOOL_BRIDGE_ENABLED:-false} == true ]] || { printf 'Tool bridge is disabled; Codex bridge test skipped.\n'; exit 0; }
[[ ${TOOL_WRITE_MODE:-read_only} == read_write ]] || { printf 'TOOL_WRITE_MODE=read_write is required.\n' >&2; exit 1; }

workspace=$(realpath -m "$WORKSPACE_DIR")
test_dir=$(mktemp -d "$workspace/.local-ai-codex-test.XXXXXX")
relative=$(realpath --relative-to="$workspace" "$test_dir")
cleanup() { rm -rf "$test_dir"; }
trap cleanup EXIT

bridge_call() {
  local mode=$1 command=$2
  local payload
  payload=$(python3 -c 'import json, sys; print(json.dumps({"command": sys.argv[1], "mode": sys.argv[2], "timeout_seconds": 60}))' "$command" "$mode")
  curl -fsS --max-time 75 \
    -H "Authorization: Bearer ${TOOL_SANDBOX_API_KEY}" \
    -H 'Content-Type: application/json' \
    --data "$payload" \
    "http://${TOOL_BRIDGE_BIND}:${TOOL_BRIDGE_PORT}/run"
}

printf '1. Unauthorized bridge calls are rejected\n'
unauthorized_payload='{"command":"true","mode":"read"}'
status=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 \
  -H 'Authorization: Bearer invalid-key' -H 'Content-Type: application/json' \
  --data "$unauthorized_payload" "http://${TOOL_BRIDGE_BIND}:${TOOL_BRIDGE_PORT}/run")
[[ $status == 401 ]]

printf '2. Writable sandbox can edit and commit separate repositories\n'
setup_command=$(cat <<EOF
set -eu
base=/workspace/${relative}
for repo in one two; do
  git init -q "\$base/\$repo"
  git -C "\$base/\$repo" config user.name 'Local AI Codex Test'
  git -C "\$base/\$repo" config user.email 'codex-test@local.invalid'
  printf '%s\\n' "\$repo" > "\$base/\$repo/result.txt"
  git -C "\$base/\$repo" add result.txt
  git -C "\$base/\$repo" commit -qm "Codex: initialize \$repo"
done
EOF
)
setup_response=$(bridge_call write "$setup_command")
python3 -c 'import json, sys; reply=json.load(sys.stdin); assert reply["exit_code"] == 0, reply' <<<"$setup_response"
for repo in one two; do
  git -C "$test_dir/$repo" log -1 --pretty=%s | grep -qx "Codex: initialize $repo"
done

printf '3. Missing Git identity prevents a commit\n'
identity_command=$(cat <<EOF
set -eu
repo=/workspace/${relative}/no-identity
git init -q "\$repo"
printf pending > "\$repo/pending.txt"
git -C "\$repo" add pending.txt
git -C "\$repo" commit -m 'must not commit without identity'
EOF
)
identity_response=$(bridge_call write "$identity_command")
python3 -c 'import json, sys; reply=json.load(sys.stdin); assert reply["exit_code"] != 0, reply' <<<"$identity_response"
! git -C "$test_dir/no-identity" rev-parse --verify HEAD >/dev/null 2>&1

printf '4. Output is capped and recorded in the audit log\n'
output_response=$(bridge_call read "python3 -c \"print('x' * 12000)\"")
python3 -c 'import json, os, sys; reply=json.load(sys.stdin); cap=int(os.environ["TOOL_MAX_OUTPUT_CHARS"]); assert reply["exit_code"] == 0, reply; assert len(reply["stdout"]) + len(reply["stderr"]) <= cap, reply' <<<"$output_response"
rg -q "local-ai-codex-test" "${TOOL_AUDIT_DIR}/tool-bridge.jsonl"

printf 'Codex tool bridge test passed.\n'
