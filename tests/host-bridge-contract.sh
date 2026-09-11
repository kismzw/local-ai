#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

grep -Fq 'ensure_variable HOST_TOOL_API_KEY CHANGE_ME' scripts/setup.sh
grep -Fq 'host-bridge open-webui' scripts/start.sh
grep -Fq 'local-ai-host-bridge.service' scripts/stop.sh
grep -Fq 'HOST_TOOL_MAX_TIMEOUT_SECONDS' config/open-webui/full-desktop-shell-tool.py
grep -Fq "HOST_TOOL_MAX_TIMEOUT_SECONDS=\"\$HOST_TOOL_MAX_TIMEOUT_SECONDS\"" scripts/service-command.sh
grep -Fq 'phase": "start"' host-bridge/app.py
grep -Fq 'os.fsync(stream.fileno())' host-bridge/app.py
