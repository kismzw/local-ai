#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

for service in llama embedding docling searxng tool-bridge; do
  grep -Fq "ExecStartPre=@LOCAL_AI_ROOT@/scripts/verify-service-artifact.sh $service" "systemd/user/local-ai-${service}.service"
done
grep -Fq 'scripts/image-receipts.py verify' scripts/verify-service-artifact.sh
