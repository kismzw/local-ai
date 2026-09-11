#!/usr/bin/env bash
set -Eeuo pipefail
exec "$(dirname -- "${BASH_SOURCE[0]}")/start-service.sh" embedding
