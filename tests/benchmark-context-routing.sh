#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

grep -Fq "MODEL_CONTEXT_SIZE_OVERRIDE=\"\$context_size\"" scripts/benchmark.sh
grep -Fq './scripts/start-llama.sh' scripts/benchmark.sh
grep -Fq "\"\$CHAT_MODEL_ALIAS\"" scripts/benchmark.sh
grep -Fq "MODEL_CONTEXT_SIZE_OVERRIDE:-\$MODEL_CONTEXT_SIZE" scripts/service-command.sh
