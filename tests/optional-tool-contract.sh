#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

grep -Fq "if [[ \$TOOL_BRIDGE_ENABLED == true ]]; then build_tool \"\$TOOL_IMAGE\"; fi" scripts/pull-images.sh
grep -Fq "if [[ \$TOOL_BRIDGE_ENABLED == true ]]; then" tests/smoke.sh
grep -Fq './tests/tool-isolation.sh' tests/smoke.sh
