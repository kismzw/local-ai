#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
[[ "$TOOL_BRIDGE_ENABLED" == true ]] || { printf 'Tool bridge is disabled; set TOOL_BRIDGE_ENABLED=true after reviewing docs/TOOLS.md.\n'; exit 0; }
require_file "$TOOL_IMAGE"
uv_bin=${UV_BIN:-"$HOME/.local/bin/uv"}
[[ -x "$uv_bin" ]] || { printf 'uv is not installed. Run ./scripts/install-uv.sh.\n' >&2; exit 1; }
start_background tool-bridge env APPTAINER_BIN="$APPTAINER_BIN" TOOL_IMAGE="$(absolute_path "$TOOL_IMAGE")" WORKSPACE_DIR="$(absolute_path "$WORKSPACE_DIR")" TOOL_AUDIT_DIR="$(absolute_path "$TOOL_AUDIT_DIR")" TOOL_SANDBOX_API_KEY="$TOOL_SANDBOX_API_KEY" TOOL_WRITE_MODE="$TOOL_WRITE_MODE" TOOL_NETWORK_MODE="$TOOL_NETWORK_MODE" UV_CACHE_DIR="$(absolute_path .uv/cache)" "$uv_bin" run --project tool-bridge --python 3.11 uvicorn --app-dir tool-bridge app:APP --host "$TOOL_BRIDGE_BIND" --port "$TOOL_BRIDGE_PORT"
