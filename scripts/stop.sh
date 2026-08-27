#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
if (($#)); then
  services=("$@")
else
  services=(open-webui tool-bridge docling-gate docling embedding-server llama-server searxng)
fi
for service in "${services[@]}"; do
  pidfile="run/${service}.pid"
  if pid_running "$pidfile"; then
    pid=$(<"$pidfile")
    # start_background uses setsid, so its PID is a service-specific process
    # group leader. Stop the wrapper and all of its children together.
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid"
    for _ in {1..20}; do
      pid_running "$pidfile" || break
      sleep 0.25
    done
    if pid_running "$pidfile"; then
      kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
    fi
    printf 'Stopped %s (pid %s).\n' "$service" "$pid"
  fi
  rm -f "$pidfile"
done
