#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
set -a; source .env; set +a
workspace=$(realpath -m "$WORKSPACE_DIR")
image=$(realpath -m "$TOOL_IMAGE")
real_user_home=$(realpath -m "$HOME")
[[ -f "$image" ]] || { printf 'Tool SIF is missing: %s\n' "$image" >&2; exit 1; }
mkdir -p "$workspace"
probe_file="$workspace/.local-ai-isolation-check"
host_sentinel="$root_dir/data/.host-isolation-sentinel"
printf 'host-unchanged\n' > "$host_sentinel"
cleanup() { rm -f "$probe_file" "$host_sentinel"; }
trap cleanup EXIT
"$APPTAINER_BIN" exec --cleanenv --containall --no-home --writable-tmpfs --pwd /workspace --env "LOCAL_AI_REAL_HOME=$real_user_home" --bind "$workspace:/workspace:rw" "$image" /bin/sh -lc 'test -d /workspace; printf ok > .local-ai-isolation-check; python3 -c "print(2 + 2)" | grep -qx 4; git --version >/dev/null; test ! -e "$LOCAL_AI_REAL_HOME"; test ! -e "$LOCAL_AI_REAL_HOME/.ssh"; test ! -e /root/.ssh; test ! -e /var/run/docker.sock; printf ephemeral > /etc/local-ai-ephemeral'
test -f "$probe_file"
test "$(<"$host_sentinel")" = host-unchanged
printf 'Tool filesystem isolation test passed.\n'
if [[ ${1:-} != --quick ]]; then
  network_output=$(mktemp)
  if "$APPTAINER_BIN" exec --cleanenv --containall --no-home --writable-tmpfs --net --network none --bind "$workspace:/workspace:rw" "$image" /bin/sh -lc 'python3 -c "import urllib.request; urllib.request.urlopen(\"https://example.com\", timeout=3)"' >"$network_output" 2>&1; then
    rm -f "$network_output"
    printf 'NETWORK ISOLATION FAILED: request unexpectedly succeeded.\n' >&2
    exit 1
  elif rg -q 'Temporary failure in name resolution|Network is unreachable|Name or service not known|Connection refused' "$network_output"; then
    rm -f "$network_output"
    printf 'Tool network isolation test passed (--net --network none blocks egress).\n'
  else
    printf 'NETWORK ISOLATION: NOT GUARANTEED. Apptainer network probe failed unexpectedly:\n' >&2
    sed -n '1,120p' "$network_output" >&2
    rm -f "$network_output"
    exit 2
  fi
fi
