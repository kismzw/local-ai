#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
set -a; source .env; set +a
api="http://${LLAMA_SERVER_BIND}:${LLAMA_SERVER_PORT}"
printf '1. Model discovery\n'
curl -fsS -H "Authorization: Bearer ${LLAMA_API_KEY}" "$api/v1/models" | grep -q qwen3.8-27b
printf '2. Non-streaming chat\n'
curl -fsS -H "Authorization: Bearer ${LLAMA_API_KEY}" -H 'Content-Type: application/json' -d '{"model":"qwen3.8-27b","messages":[{"role":"user","content":"Reply only with OK."}],"chat_template_kwargs":{"enable_thinking":false},"max_tokens":8,"temperature":0}' "$api/v1/chat/completions" | grep -q '"content":"OK"'
printf '3. Streaming chat\n'
stream_file=$(mktemp)
trap 'rm -f "$stream_file"' EXIT
curl -fsSN -H "Authorization: Bearer ${LLAMA_API_KEY}" -H 'Content-Type: application/json' -d '{"model":"qwen3.8-27b","messages":[{"role":"user","content":"Reply only with OK."}],"chat_template_kwargs":{"enable_thinking":false},"max_tokens":8,"stream":true,"temperature":0}' "$api/v1/chat/completions" > "$stream_file"
grep -q 'data:' "$stream_file"
printf '4. GPU is visible to inference\n'
apptainer exec --nv "$LLAMA_IMAGE" nvidia-smi >/dev/null
printf '5. Open WebUI health\n'
curl -fsS "http://${OPEN_WEBUI_BIND}:${OPEN_WEBUI_PORT}/health" >/dev/null
printf '6. Embeddings endpoint\n'
python3 -c "import urllib.request, os; r=urllib.request.Request('http://${LLAMA_SERVER_BIND}:${EMBEDDING_SERVER_PORT}/v1/embeddings', data=b'{\"model\":\"qwen3-embedding-0.6b\",\"input\":\"RAG smoke test\"}', headers={'Authorization':'Bearer '+os.environ['EMBEDDING_API_KEY'],'Content-Type':'application/json'}); assert b'\"embedding\"' in urllib.request.urlopen(r, timeout=30).read()"
printf '7. Tool sandbox and host isolation\n'
./tests/tool-isolation.sh
printf 'Smoke checks passed. See docs/TESTING.md for browser RAG and persistence checks.\n'
