#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"
command=${1:-prepare}
rendered="$root_dir/run/systemd-units"
prepare() {
  python3 scripts/config-check.py --write-systemd-env
  session_vars=()
  for name in SSH_AUTH_SOCK DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS; do
    [[ -n ${!name:-} ]] && session_vars+=("$name")
  done
  if ((${#session_vars[@]})); then systemctl --user import-environment "${session_vars[@]}"; fi
  mkdir -p "$rendered"
  escaped_root=${root_dir//\\/\\\\}
  escaped_root=${escaped_root//&/\\&}
  escaped_root=${escaped_root//|/\\|}
  systemd_root=${root_dir// /\\x20}
  escaped_systemd_root=${systemd_root//\\/\\\\}
  escaped_systemd_root=${escaped_systemd_root//&/\\&}
  escaped_systemd_root=${escaped_systemd_root//|/\\|}
  for unit in systemd/user/*; do
    sed -e "s|@LOCAL_AI_ROOT_SYSTEMD@|$escaped_systemd_root|g" -e "s|@LOCAL_AI_ROOT@|$escaped_root|g" "$unit" > "$rendered/$(basename "$unit")"
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
