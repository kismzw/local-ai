#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
require_file "$LLAMA_IMAGE"; require_file "$MODEL_DIR/$MODEL_FILE"
model_dir=$(absolute_path "$MODEL_DIR")
context_size=${MODEL_CONTEXT_SIZE_OVERRIDE:-$MODEL_CONTEXT_SIZE}
start_background llama-server "$APPTAINER_BIN" exec --nv --cleanenv --containall --no-home --env LD_LIBRARY_PATH=/app \
  --bind "$model_dir:/models:ro" "$LLAMA_IMAGE" /app/llama-server \
  --model "/models/$MODEL_FILE" --alias qwen3.8-27b --host "$LLAMA_SERVER_BIND" --port "$LLAMA_SERVER_PORT" \
  --ctx-size "$context_size" --parallel "$MODEL_PARALLELISM" --n-gpu-layers "$MODEL_GPU_LAYERS" \
  --threads "$MODEL_THREADS" --batch-size "$MODEL_BATCH_SIZE" --ubatch-size "$MODEL_UBATCH_SIZE" \
  --cache-type-k "$MODEL_KV_CACHE_K" --cache-type-v "$MODEL_KV_CACHE_V" --flash-attn auto --metrics --api-key "$LLAMA_API_KEY" --no-webui
