#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs

if [[ ! -f "$LLAMA_IMAGE" || ${FORCE_PULL:-false} == true ]]; then
  "$APPTAINER_BIN" pull --force "$LLAMA_IMAGE" docker://ghcr.io/ggml-org/llama.cpp:server-cuda
fi
if [[ ! -f "$TOOL_IMAGE" || ${FORCE_PULL:-false} == true ]]; then
  "$APPTAINER_BIN" build --fakeroot "$TOOL_IMAGE" config/apptainer/tool-sandbox.def
fi
if [[ ! -f "$SEARXNG_IMAGE" || ${FORCE_PULL:-false} == true ]]; then
  "$APPTAINER_BIN" pull --force "$SEARXNG_IMAGE" docker://searxng/searxng:latest
fi
if [[ ! -f "$DOCLING_IMAGE" || ${FORCE_PULL:-false} == true ]]; then
  "$APPTAINER_BIN" pull --force "$DOCLING_IMAGE" docker://quay.io/docling-project/docling-serve-cu128:latest
fi
printf 'Pulled immutable SIF images:\n  %s\n  %s\n' "$LLAMA_IMAGE" "$TOOL_IMAGE"
printf '  %s\n  %s\n' "$SEARXNG_IMAGE" "$DOCLING_IMAGE"
