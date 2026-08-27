#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
require_file "$SEARXNG_IMAGE"

config_dir="$(absolute_path config/searxng)"
cache_dir="$(absolute_path "$SEARXNG_CACHE_DIR")"
start_background searxng "$APPTAINER_BIN" exec --cleanenv --containall --no-home --writable-tmpfs \
    --env "SEARXNG_SECRET=$SEARXNG_SECRET" \
    --env "SEARXNG_PORT=$SEARXNG_PORT" \
    --env SEARXNG_BIND_ADDRESS=127.0.0.1 \
    --env GRANIAN_HOST=127.0.0.1 \
    --env "GRANIAN_PORT=$SEARXNG_PORT" \
    --env PYTHONPATH=/usr/local/searxng \
    --bind "$config_dir:/etc/searxng:ro" \
    --bind "$cache_dir:/var/cache/searxng:rw" \
    "$SEARXNG_IMAGE" /usr/local/searxng/entrypoint.sh
