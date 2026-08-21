#!/usr/bin/env bash
set -Eeuo pipefail
uv_dir="${UV_INSTALL_DIR:-$HOME/.local/bin}"
mkdir -p "$uv_dir"
installer=$(mktemp)
trap 'rm -f "$installer"' EXIT
curl -LsSf https://astral.sh/uv/install.sh -o "$installer"
UV_INSTALL_DIR="$uv_dir" sh "$installer"
"$uv_dir/uv" python install 3.11
printf 'Installed user-space uv and managed Python 3.11 at %s.\n' "$uv_dir"
