#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
load_env; ensure_dirs
require_file "$DOCLING_IMAGE"

artifacts_dir="$(absolute_path "$DOCLING_ARTIFACTS_DIR")"
"$APPTAINER_BIN" exec --nv --cleanenv --containall --no-home --writable-tmpfs \
  --bind "$artifacts_dir:/artifacts:rw" \
  "$DOCLING_IMAGE" /opt/app-root/bin/docling-tools models download \
    -o /artifacts layout tableformer rapidocr easyocr
printf 'Downloaded Docling layout, tableformer, RapidOCR, and EasyOCR models to %s.\n' "$DOCLING_ARTIFACTS_DIR"
