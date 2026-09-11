#!/usr/bin/env bash
set -Eeuo pipefail

service=${1:?service name is required}
case "$service" in
  llama) printf '%s\n' llama-server ;;
  embedding) printf '%s\n' embedding-server ;;
  docling|docling-gate|searxng|tool-bridge|host-bridge|open-webui) printf '%s\n' "$service" ;;
  *)
    printf 'Unknown service: %s\n' "$service" >&2
    exit 2
    ;;
esac
