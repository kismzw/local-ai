#!/usr/bin/env bash
set -Eeuo pipefail
root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
memory_file="$root_dir/data/memory/memory.yaml"
backup_dir="$root_dir/data/memory/backups"
mkdir -p "$backup_dir"
usage() { printf 'Usage: %s {show|edit|delete|backup|disable}\n' "$0"; }
case ${1:-} in
  show) [[ -f "$memory_file" ]] && sed -n '1,240p' "$memory_file" || printf 'No explicit long-term memory saved.\n' ;;
  edit) ${EDITOR:-vi} "$memory_file" ;;
  delete) [[ -f "$memory_file" ]] && rm -f "$memory_file"; printf 'Explicit memory removed.\n' ;;
  backup) [[ -f "$memory_file" ]] || { printf 'No explicit memory to back up.\n' >&2; exit 1; }; cp "$memory_file" "$backup_dir/memory-$(date +%Y%m%d-%H%M%S).yaml" ;;
  disable) printf 'Long-term memory is manual: do not attach data/memory/memory.yaml as Open WebUI Knowledge.\n' ;;
  *) usage; exit 2 ;;
esac
