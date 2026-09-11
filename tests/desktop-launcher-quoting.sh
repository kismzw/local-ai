#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root_dir"

# Desktop Exec values must quote the executable independently of its arguments.
grep -Fq "launcher_command=\"\\\"\${launcher_command}/local-ai\\\"\"" local-ai
grep -Fq "Exec=\$launcher_command open" local-ai
grep -Fq "Exec=\$launcher_command close" local-ai
