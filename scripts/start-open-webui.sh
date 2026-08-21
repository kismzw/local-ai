#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
uv_bin=${UV_BIN:-"$HOME/.local/bin/uvx"}
[[ -x "$uv_bin" ]] || { printf 'uvx is not installed. Run ./scripts/install-uv.sh.\n' >&2; exit 1; }
start_background open-webui env \
  DATA_DIR="$(absolute_path "$OPEN_WEBUI_DATA_DIR")" WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" WEBUI_NAME='Local AI' \
  CORS_ALLOW_ORIGIN='http://127.0.0.1:3000;http://localhost:3000' \
  ENABLE_SIGNUP=false ENABLE_INITIAL_ADMIN_SIGNUP=true DEFAULT_USER_ROLE=pending \
  ENABLE_COMMUNITY_SHARING=false ENABLE_ADMIN_EXPORT=false ENABLE_MEMORIES=false ENABLE_MEMORY_SYSTEM_CONTEXT=false OFFLINE_MODE=true \
  RAG_FILE_MAX_SIZE=50 RAG_FILE_MAX_COUNT=10 RAG_ALLOWED_FILE_EXTENSIONS='.pdf,.txt,.md,.docx,.csv,.py,.sh,.json,.yaml,.yml' \
  OPENAI_API_BASE_URLS="http://${LLAMA_SERVER_BIND}:${LLAMA_SERVER_PORT}/v1" OPENAI_API_KEYS="$LLAMA_API_KEY" \
  RAG_EMBEDDING_ENGINE=openai RAG_OPENAI_API_BASE_URL="http://${LLAMA_SERVER_BIND}:${EMBEDDING_SERVER_PORT}/v1" RAG_OPENAI_API_KEY="$EMBEDDING_API_KEY" RAG_EMBEDDING_MODEL="$RAG_EMBEDDING_MODEL" RAG_CHUNK_SIZE="$RAG_CHUNK_SIZE" RAG_CHUNK_OVERLAP="$RAG_CHUNK_OVERLAP" \
  UV_CACHE_DIR="$(absolute_path .uv/cache)" "$uv_bin" --python 3.11 --from "open-webui==${OPEN_WEBUI_VERSION}" open-webui serve --host "$OPEN_WEBUI_BIND" --port "$OPEN_WEBUI_PORT"
