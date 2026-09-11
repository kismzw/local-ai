#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env
configured_context_size=$MODEL_CONTEXT_SIZE
context_size=${1:-$configured_context_size}
[[ "$context_size" =~ ^(32768|65536)$ ]] || { printf 'Usage: %s [32768|65536]\n' "$0" >&2; exit 2; }
restore_configured_context() {
  systemctl --user unset-environment MODEL_CONTEXT_SIZE_OVERRIDE || true
  if [[ "$context_size" != "$configured_context_size" ]]; then
    printf 'Restoring configured %s-token context...\n' "$configured_context_size" >&2
    ./scripts/stop.sh || true
    ./scripts/start.sh || true
  fi
}
trap restore_configured_context EXIT
mkdir -p benchmarks/results
output="benchmarks/results/$(date +%Y%m%d-%H%M%S)-${context_size}.md"
api="http://${LLAMA_SERVER_BIND}:${LLAMA_SERVER_PORT}"
if [[ "$context_size" != "$configured_context_size" ]]; then
  ./scripts/stop.sh
  systemctl --user set-environment MODEL_CONTEXT_SIZE_OVERRIDE="$context_size"
  ./scripts/start-llama.sh
fi
for attempt in $(seq 1 60); do
  if curl -fsS "$api/health" >/dev/null 2>&1; then break; fi
  sleep 2
done
curl -fsS "$api/health" >/dev/null
printf '# llama.cpp benchmark (%s context)\n\n' "$context_size" > "$output"
printf 'Measured at: %s\n\n' "$(date --iso-8601=seconds)" >> "$output"
printf '## GPU before\n\n```text\n' >> "$output"; nvidia-smi --query-gpu=name,memory.used,memory.free,utilization.gpu,utilization.memory --format=csv,noheader >> "$output"; printf '```\n\n' >> "$output"
printf '## Short generation\n\n```json\n' >> "$output"
curl --fail --silent --show-error --write-out '\nTTFT/total transport time: %{time_starttransfer}s / %{time_total}s\n' -H "Authorization: Bearer ${LLAMA_API_KEY}" -H 'Content-Type: application/json' -d '{"model":"qwen3.8-27b","messages":[{"role":"user","content":"Explain KV cache in one sentence."}],"max_tokens":128,"temperature":0}' "$api/v1/chat/completions" >> "$output"
printf '\n```\n\n## Server metrics\n\n```text\n' >> "$output"
curl --fail --silent -H "Authorization: Bearer ${LLAMA_API_KEY}" "$api/metrics" >> "$output" || true
printf '\n```\n\n## Long-prompt processing (~70%% of configured context)\n\n```json\n' >> "$output"
long_request=$(mktemp)
trap 'rm -f "$long_request"; restore_configured_context' EXIT
python3 - "$context_size" > "$long_request" <<'PY'
import json, sys
tokens = int(int(sys.argv[1]) * 0.70)
# Repeated simple token gives a reproducible near-context prompt without
# exceeding the target context due to multi-token words.
prompt = ("x " * tokens).strip()
print(json.dumps({"model":"qwen3.8-27b", "messages":[{"role":"user", "content":prompt + "\nReturn only: CONTEXT_OK"}], "max_tokens":16, "temperature":0}))
PY
curl --fail --silent --show-error --write-out '\nLong-prompt TTFT/total: %{time_starttransfer}s / %{time_total}s\n' -H "Authorization: Bearer ${LLAMA_API_KEY}" -H 'Content-Type: application/json' --data @"$long_request" "$api/v1/chat/completions" >> "$output"
printf '\n```\n\n## GPU after\n\n```text\n' >> "$output"; nvidia-smi --query-gpu=name,memory.used,memory.free,utilization.gpu,utilization.memory --format=csv,noheader >> "$output"; printf '```\n' >> "$output"
printf 'Wrote %s\n' "$output"
