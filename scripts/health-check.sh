#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env
service=${1:?service name is required}
case "$service" in
 llama-server) url="http://${LLAMA_SERVER_BIND}:${LLAMA_SERVER_PORT}/health" ;;
 embedding-server) url="http://${LLAMA_SERVER_BIND}:${EMBEDDING_SERVER_PORT}/health" ;;
 docling) url="http://127.0.0.1:${DOCLING_PORT}/health" ;;
 docling-gate) url="http://127.0.0.1:${DOCLING_GATE_PORT}/health/ready" ;;
 searxng) url="http://127.0.0.1:${SEARXNG_PORT}/healthz" ;;
 tool-bridge) [[ $TOOL_BRIDGE_ENABLED == true ]] || exit 0; url="http://${TOOL_BRIDGE_BIND}:${TOOL_BRIDGE_PORT}/health/ready" ;;
 host-bridge) [[ $HOST_TOOL_ENABLED == true ]] || exit 0; url="http://${HOST_TOOL_BIND}:${HOST_TOOL_PORT}/health/ready" ;;
 open-webui) url="http://${OPEN_WEBUI_BIND}:${OPEN_WEBUI_PORT}/health" ;;
 *) exit 2 ;;
esac
for _ in {1..60}; do curl -fsS --max-time 2 "$url" >/dev/null && exit 0; sleep 1; done
printf '%s did not become ready: %s\n' "$service" "$url" >&2
exit 1
