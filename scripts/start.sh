#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
./scripts/doctor.sh --preflight
./scripts/start-llama.sh
./scripts/start-embedding.sh
if grep -q '^TOOL_BRIDGE_ENABLED=true$' .env; then ./scripts/start-tool-bridge.sh; fi
./scripts/start-open-webui.sh
printf 'Open WebUI: http://127.0.0.1:%s\n' "$(awk -F= '/^OPEN_WEBUI_PORT=/{print $2}' .env)"
