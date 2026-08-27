#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
require_file "$DOCLING_IMAGE"

artifacts_dir="$(absolute_path "$DOCLING_ARTIFACTS_DIR")"
start_background docling "$APPTAINER_BIN" exec --nv --cleanenv --containall --no-home --writable-tmpfs \
  --env DOCLING_SERVE_ENG_LOC_NUM_WORKERS=1 \
  --env "DOCLING_SERVE_MAX_SYNC_WAIT=$DOCLING_MAX_SYNC_WAIT_SECONDS" \
  --env OMP_NUM_THREADS=4 \
  --env MKL_NUM_THREADS=4 \
  --env UVICORN_WORKERS=1 \
  --bind "$artifacts_dir:/artifacts:rw" \
  "$DOCLING_IMAGE" /opt/app-root/bin/docling-serve run \
    --host 127.0.0.1 --port "$DOCLING_PORT" --workers 1 --no-proxy-headers \
    --artifacts-path /artifacts
