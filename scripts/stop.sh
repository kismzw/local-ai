#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
if (($#)); then
  for service in "$@"; do systemctl --user stop "local-ai-${service}.service" || true; done
else
  systemctl --user stop local-ai.target local-ai-open-webui.service local-ai-tool-bridge.service local-ai-docling-gate.service local-ai-docling.service local-ai-embedding.service local-ai-llama.service local-ai-searxng.service || true
fi
