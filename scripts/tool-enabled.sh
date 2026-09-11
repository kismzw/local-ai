#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env
[[ $TOOL_BRIDGE_ENABLED == true ]]
