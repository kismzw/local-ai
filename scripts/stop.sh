#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
for service in open-webui tool-bridge embedding-server llama-server; do
  pidfile="run/${service}.pid"
  if pid_running "$pidfile"; then
    pid=$(<"$pidfile")
    kill "$pid"
    printf 'Stopped %s (pid %s).\n' "$service" "$pid"
  fi
  rm -f "$pidfile"
done
