#!/usr/bin/env bash
set -Eeuo pipefail
service=${1:-}
[[ -n $service ]] || { printf 'Usage: %s {llama|embedding|docling|docling-gate|searxng|tool-bridge|open-webui}\n' "$0" >&2; exit 2; }
exec journalctl --user -u "local-ai-${service}.service" -n 200 -f
