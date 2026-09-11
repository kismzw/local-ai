#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

if rg -F 'scripts/systemd.sh prepare' scripts/stop.sh; then
  printf 'stop.sh must not prepare units from the current configuration\n' >&2
  exit 1
fi
fake_dir=$(mktemp -d)
cleanup() { rm -rf -- "$fake_dir"; }
trap cleanup EXIT
printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$*" > "%s/call"\n' "$fake_dir" > "$fake_dir/systemctl"
chmod +x "$fake_dir/systemctl"
PATH="$fake_dir:$PATH" ./scripts/stop.sh llama
grep -Fxq -- '--user stop local-ai-llama.service' "$fake_dir/call"
