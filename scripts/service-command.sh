#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
service=${1:?service name is required}
uv_bin=${UV_BIN:-"$HOME/.local/bin/uv"}
case "$service" in
  llama-server)
    require_file "$LLAMA_IMAGE"; require_file "$MODEL_DIR/$MODEL_FILE"; model_dir=$(absolute_path "$MODEL_DIR")
    exec "$APPTAINER_BIN" exec --nv --cleanenv --containall --no-home --env LD_LIBRARY_PATH=/app --bind "$model_dir:/models:ro" "$LLAMA_IMAGE" /app/llama-server --model "/models/$MODEL_FILE" --alias "$CHAT_MODEL_ALIAS" --host "$LLAMA_SERVER_BIND" --port "$LLAMA_SERVER_PORT" --ctx-size "${MODEL_CONTEXT_SIZE_OVERRIDE:-$MODEL_CONTEXT_SIZE}" --parallel "$MODEL_PARALLELISM" --n-gpu-layers "$MODEL_GPU_LAYERS" --threads "$MODEL_THREADS" --batch-size "$MODEL_BATCH_SIZE" --ubatch-size "$MODEL_UBATCH_SIZE" --cache-type-k "$MODEL_KV_CACHE_K" --cache-type-v "$MODEL_KV_CACHE_V" --flash-attn auto --metrics --api-key "$LLAMA_API_KEY" --no-webui
    ;;
  embedding-server)
    require_file "$LLAMA_IMAGE"; require_file "$MODEL_DIR/$EMBEDDING_MODEL_FILE"; model_dir=$(absolute_path "$MODEL_DIR")
    exec "$APPTAINER_BIN" exec --nv --cleanenv --containall --no-home --env LD_LIBRARY_PATH=/app --bind "$model_dir:/models:ro" "$LLAMA_IMAGE" /app/llama-server --model "/models/$EMBEDDING_MODEL_FILE" --alias "$EMBEDDING_MODEL_ALIAS" --host "$LLAMA_SERVER_BIND" --port "$EMBEDDING_SERVER_PORT" --ctx-size 8192 --parallel 2 --n-gpu-layers all --embedding --pooling last --flash-attn auto --api-key "$EMBEDDING_API_KEY" --no-webui
    ;;
  docling)
    require_file "$DOCLING_IMAGE"; artifacts_dir=$(absolute_path "$DOCLING_ARTIFACTS_DIR")
    exec "$APPTAINER_BIN" exec --nv --cleanenv --containall --no-home --writable-tmpfs --env DOCLING_SERVE_ENG_LOC_NUM_WORKERS=1 --env "DOCLING_SERVE_MAX_SYNC_WAIT=$DOCLING_MAX_SYNC_WAIT_SECONDS" --env OMP_NUM_THREADS=4 --env MKL_NUM_THREADS=4 --env UVICORN_WORKERS=1 --bind "$artifacts_dir:/artifacts:rw" "$DOCLING_IMAGE" /opt/app-root/bin/docling-serve run --host 127.0.0.1 --port "$DOCLING_PORT" --workers 1 --no-proxy-headers --artifacts-path /artifacts
    ;;
  docling-gate)
    [[ -x $uv_bin ]] || { printf 'uv is not installed.\n' >&2; exit 1; }; audit_dir=$(absolute_path "$DOCLING_AUDIT_DIR")
    exec env DOCLING_GATE_API_KEY="$DOCLING_GATE_API_KEY" DOCLING_BACKEND_URL="http://127.0.0.1:${DOCLING_PORT}" LLAMA_METRICS_URL="http://${LLAMA_SERVER_BIND}:${LLAMA_SERVER_PORT}/metrics" LLAMA_SLOTS_URL="http://${LLAMA_SERVER_BIND}:${LLAMA_SERVER_PORT}/slots" LLAMA_METRICS_API_KEY="$LLAMA_API_KEY" DOCLING_GATE_IDLE_SECONDS="$DOCLING_GATE_IDLE_SECONDS" DOCLING_GATE_POLL_SECONDS="$DOCLING_GATE_POLL_SECONDS" DOCLING_GATE_MAX_WAIT_SECONDS="$DOCLING_GATE_MAX_WAIT_SECONDS" DOCLING_GATE_MAX_RETRIES="$DOCLING_GATE_MAX_RETRIES" DOCLING_GATE_MAX_UNKNOWN_POLLS="$DOCLING_GATE_MAX_UNKNOWN_POLLS" DOCLING_AUDIT_DIR="$audit_dir" LOG_MAX_BYTES="$LOG_MAX_BYTES" LOG_ROTATION_COUNT="$LOG_ROTATION_COUNT" UV_CACHE_DIR="$(absolute_path .uv/cache)" "$uv_bin" run --project docling-gate --locked --no-sync uvicorn --app-dir docling-gate app:APP --host 127.0.0.1 --port "$DOCLING_GATE_PORT"
    ;;
  searxng)
    require_file "$SEARXNG_IMAGE"; config_dir=$(absolute_path config/searxng); cache_dir=$(absolute_path "$SEARXNG_CACHE_DIR")
    exec "$APPTAINER_BIN" exec --cleanenv --containall --no-home --writable-tmpfs --env "SEARXNG_SECRET=$SEARXNG_SECRET" --env "SEARXNG_PORT=$SEARXNG_PORT" --env SEARXNG_BIND_ADDRESS=127.0.0.1 --env GRANIAN_HOST=127.0.0.1 --env "GRANIAN_PORT=$SEARXNG_PORT" --env PYTHONPATH=/usr/local/searxng --bind "$config_dir:/etc/searxng:ro" --bind "$cache_dir:/var/cache/searxng:rw" "$SEARXNG_IMAGE" /usr/local/searxng/entrypoint.sh
    ;;
  tool-bridge)
    [[ $TOOL_BRIDGE_ENABLED == true ]] || exit 0; require_file "$TOOL_IMAGE"; [[ -x $uv_bin ]] || exit 1; tool_data_dir=${TOOL_DATA_DIR:-}; [[ -z $tool_data_dir ]] || tool_data_dir=$(absolute_path "$tool_data_dir")
    exec env APPTAINER_BIN="$APPTAINER_BIN" TOOL_IMAGE="$(absolute_path "$TOOL_IMAGE")" WORKSPACE_DIR="$(absolute_path "$WORKSPACE_DIR")" TOOL_DATA_DIR="$tool_data_dir" TOOL_HIDDEN_PATHS="${TOOL_HIDDEN_PATHS:-}" TOOL_AUDIT_DIR="$(absolute_path "$TOOL_AUDIT_DIR")" TOOL_SANDBOX_API_KEY="$TOOL_SANDBOX_API_KEY" TOOL_WRITE_MODE="$TOOL_WRITE_MODE" TOOL_NETWORK_MODE="$TOOL_NETWORK_MODE" TOOL_MAX_OUTPUT_CHARS="$TOOL_MAX_OUTPUT_CHARS" LOG_MAX_BYTES="$LOG_MAX_BYTES" LOG_ROTATION_COUNT="$LOG_ROTATION_COUNT" OPEN_WEBUI_PORT="$OPEN_WEBUI_PORT" UV_CACHE_DIR="$(absolute_path .uv/cache)" "$uv_bin" run --project tool-bridge --locked --no-sync uvicorn --app-dir tool-bridge app:APP --host "$TOOL_BRIDGE_BIND" --port "$TOOL_BRIDGE_PORT"
    ;;
  open-webui)
    [[ -x $uv_bin ]] || { printf 'uv is not installed.\n' >&2; exit 1; }
    exec env DATA_DIR="$(absolute_path "$OPEN_WEBUI_DATA_DIR")" WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" WEBUI_NAME='Local AI' TOOL_BRIDGE_URL="http://${TOOL_BRIDGE_BIND}:${TOOL_BRIDGE_PORT}/run" TOOL_SANDBOX_API_KEY="${TOOL_SANDBOX_API_KEY:-}" CORS_ALLOW_ORIGIN="http://127.0.0.1:${OPEN_WEBUI_PORT};http://localhost:${OPEN_WEBUI_PORT}" ENABLE_SIGNUP=false ENABLE_INITIAL_ADMIN_SIGNUP=true DEFAULT_USER_ROLE=pending ENABLE_COMMUNITY_SHARING=false ENABLE_ADMIN_EXPORT=false ENABLE_MEMORIES=false ENABLE_MEMORY_SYSTEM_CONTEXT=false OFFLINE_MODE=true RAG_FILE_MAX_SIZE=50 RAG_FILE_MAX_COUNT=10 RAG_ALLOWED_FILE_EXTENSIONS='.pdf,.txt,.md,.docx,.csv,.py,.sh,.json,.yaml,.yml' CONTENT_EXTRACTION_ENGINE=docling DOCLING_SERVER_URL="http://127.0.0.1:${DOCLING_GATE_PORT}" DOCLING_API_KEY="$DOCLING_GATE_API_KEY" DOCLING_PARAMS='{"do_ocr":true,"ocr_engine":"easyocr","ocr_lang":["en","ja"],"pdf_backend":"dlparse_v4","table_mode":"accurate","pipeline":"standard"}' OPENAI_API_BASE_URLS="http://${LLAMA_SERVER_BIND}:${LLAMA_SERVER_PORT}/v1" OPENAI_API_KEYS="$LLAMA_API_KEY" RAG_EMBEDDING_ENGINE=openai RAG_OPENAI_API_BASE_URL="http://${LLAMA_SERVER_BIND}:${EMBEDDING_SERVER_PORT}/v1" RAG_OPENAI_API_KEY="$EMBEDDING_API_KEY" RAG_EMBEDDING_MODEL="$RAG_EMBEDDING_MODEL" RAG_CHUNK_SIZE="$RAG_CHUNK_SIZE" RAG_CHUNK_OVERLAP="$RAG_CHUNK_OVERLAP" ENABLE_WEB_SEARCH="$WEB_SEARCH_ENABLED" WEB_SEARCH_ENGINE=searxng SEARXNG_QUERY_URL="http://127.0.0.1:${SEARXNG_PORT}/search?q=<query>" SEARXNG_LANGUAGE=all WEB_SEARCH_RESULT_COUNT="$WEB_SEARCH_RESULT_COUNT" WEB_SEARCH_CONCURRENT_REQUESTS="$WEB_SEARCH_CONCURRENT_REQUESTS" WEB_LOADER_CONCURRENT_REQUESTS="$WEB_LOADER_CONCURRENT_REQUESTS" WEB_LOADER_ENGINE=safe_web WEB_LOADER_TIMEOUT="$WEB_LOADER_TIMEOUT_SECONDS" WEB_FETCH_MAX_CONTENT_LENGTH="$WEB_FETCH_MAX_CONTENT_LENGTH" ENABLE_RAG_LOCAL_WEB_FETCH=false AIOHTTP_CLIENT_ALLOW_REDIRECTS=false WEB_FETCH_FILTER_LIST='!localhost,!127.0.0.1,!::1' ENABLE_WEB_SEARCH_CONFIRMATION=false DEFAULT_MODEL_PARAMS='{"function_calling":"native"}' UV_CACHE_DIR="$(absolute_path .uv/cache)" "$uv_bin" run --project open-webui-runtime --locked --no-sync open-webui serve --host "$OPEN_WEBUI_BIND" --port "$OPEN_WEBUI_PORT"
    ;;
  *) printf 'Unknown service: %s\n' "$service" >&2; exit 2 ;;
esac
