#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
require_file "$LLAMA_IMAGE"; require_file "$MODEL_DIR/$EMBEDDING_MODEL_FILE"
model_dir=$(absolute_path "$MODEL_DIR")
start_background embedding-server "$APPTAINER_BIN" exec --nv --cleanenv --containall --no-home --env LD_LIBRARY_PATH=/app \
  --bind "$model_dir:/models:ro" "$LLAMA_IMAGE" /app/llama-server \
  --model "/models/$EMBEDDING_MODEL_FILE" --alias qwen3-embedding-0.6b --host "$LLAMA_SERVER_BIND" --port "$EMBEDDING_SERVER_PORT" \
  --ctx-size 8192 --parallel 2 --n-gpu-layers all --embedding --pooling last --flash-attn auto --api-key "$EMBEDDING_API_KEY" --no-webui
