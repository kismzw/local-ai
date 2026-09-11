#!/usr/bin/env bash
# Exercise the pinned Open WebUI URL validator without touching live UI data.
set -Eeuo pipefail
# shellcheck source=../scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/../scripts/common.sh"
load_env

systemctl --user is-active --quiet local-ai-open-webui.service || { printf 'Open WebUI is not running.\n' >&2; exit 1; }
launcher_pid=$(systemctl --user show --value --property=MainPID local-ai-open-webui.service)
python_pid=$(pgrep -P "$launcher_pid" | head -n1 || true)
[[ -n "$python_pid" ]] || { printf 'Could not find Open WebUI Python child.\n' >&2; exit 1; }
# Use argv[0], not /proc/.../exe: the latter resolves the venv interpreter
# symlink to uv's shared Python and loses the Open WebUI site-packages path.
open_webui_python=$(tr '\0' '\n' < "/proc/${python_pid}/cmdline" | head -n1)
[[ -x "$open_webui_python" ]] || { printf 'Could not resolve Open WebUI Python.\n' >&2; exit 1; }
tmp_data_dir=$(mktemp -d)
trap 'rm -rf -- "$tmp_data_dir"' EXIT

if ! DATA_DIR="$tmp_data_dir" \
WEB_FETCH_FILTER_LIST='!localhost,!127.0.0.1,!::1' \
ENABLE_RAG_LOCAL_WEB_FETCH=false \
AIOHTTP_CLIENT_ALLOW_REDIRECTS=false \
"$open_webui_python" -c '
from open_webui.env import AIOHTTP_CLIENT_ALLOW_REDIRECTS
from open_webui.retrieval.web.utils import validate_url

blocked = (
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://10.0.0.1",
    "http://[fd00::1]",
    "http://169.254.169.254/latest/meta-data",
)
for url in blocked:
    try:
        validate_url(url)
    except ValueError:
        continue
    raise AssertionError(f"SSRF target unexpectedly allowed: {url}")
assert AIOHTTP_CLIENT_ALLOW_REDIRECTS is False
' >/dev/null 2>&1; then
  printf 'Open WebUI web-fetch policy validation failed.\n' >&2
  exit 1
fi
printf 'Web fetch isolation policy test passed.\n'
