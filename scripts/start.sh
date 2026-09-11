#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
# shellcheck source=common.sh
source scripts/common.sh
load_env
./scripts/doctor.sh --preflight
./scripts/systemd.sh prepare
started=()
rollback() { local status=$?; if ((status)); then for service in "${started[@]}"; do systemctl --user stop "local-ai-${service}.service" || true; done; fi; exit "$status"; }
trap rollback EXIT
for service in searxng docling llama embedding docling-gate tool-bridge open-webui; do
  [[ $service != tool-bridge || $TOOL_BRIDGE_ENABLED == true ]] || continue
  unit="local-ai-${service}.service"
  if ! systemctl --user is-active --quiet "$unit"; then started=("$service" "${started[@]}"); systemctl --user start "$unit"; fi
  health=$(./scripts/service-health-name.sh "$service")
  ./scripts/health-check.sh "$health"
done
systemctl --user start local-ai.target
trap - EXIT
printf 'Open WebUI: http://%s:%s\n' "$OPEN_WEBUI_BIND" "$OPEN_WEBUI_PORT"
