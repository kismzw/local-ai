#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
command=${1:-prepare}
rendered="$root_dir/run/systemd-units"
prepare() {
  python3 scripts/config-check.py --write-systemd-env
  mkdir -p "$rendered"
  for unit in systemd/user/*; do
    sed "s|@LOCAL_AI_ROOT@|$root_dir|g" "$unit" > "$rendered/$(basename "$unit")"
    systemctl --user link "$rendered/$(basename "$unit")" >/dev/null
  done
  systemctl --user daemon-reload
}
case "$command" in
  prepare) prepare ;;
  install) prepare; systemctl --user enable local-ai.target; printf 'Local AI will start when this user logs in.\n' ;;
  uninstall) systemctl --user disable --now local-ai.target || true; for unit in systemd/user/*; do systemctl --user disable "$(basename "$unit")" 2>/dev/null || true; done; systemctl --user daemon-reload ;;
  *) printf 'Usage: %s {prepare|install|uninstall}\n' "$0" >&2; exit 2 ;;
esac
