#!/usr/bin/env bash
set -Eeuo pipefail
uv_dir="${UV_INSTALL_DIR:-$HOME/.local/bin}"
mkdir -p "$uv_dir"
uv_version=0.12.5
python_version=3.11.16
case $(uname -m) in
  x86_64) target=x86_64-unknown-linux-gnu; checksum=68a509da24b06b4223a1c0175fb5eb5bc79342b76cbeff0cfe51ac3f5b17b6b2 ;;
  aarch64) target=aarch64-unknown-linux-gnu; checksum=9bf43b4d1a07665bf64d4c4e710930b382321a785e0eb10aac07f46471f86a31 ;;
  i686) target=i686-unknown-linux-gnu; checksum=4875a06092c3b0aa8ece5265a42b053dfef649adba26434b5e40eeb58c2a2aa5 ;;
  ppc64le) target=powerpc64le-unknown-linux-gnu; checksum=af3f868fc8af2c3a688b1a202cbed507ec5bb32522876141f1b7f4200ed0395f ;;
  riscv64) target=riscv64gc-unknown-linux-gnu; checksum=2a6fe4a685225082d82f8afba169d038d669f85bf6cff7f5f733079a7b7282d5 ;;
  s390x) target=s390x-unknown-linux-gnu; checksum=858d51fd178fe99c69923cef568fbac3f297f3767c0e0d985aa172bc1f3e2274 ;;
  *) printf 'Unsupported architecture for pinned uv install: %s\n' "$(uname -m)" >&2; exit 1 ;;
esac
archive=$(mktemp)
extract_dir=$(mktemp -d)
trap 'rm -f "$archive"; rm -rf "$extract_dir"' EXIT
url="https://github.com/astral-sh/uv/releases/download/${uv_version}/uv-${target}.tar.gz"
curl --fail --location --proto '=https' --tlsv1.2 "$url" -o "$archive"
printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check --status
tar -xzf "$archive" --strip-components=1 -C "$extract_dir"
install -m 755 "$extract_dir/uv" "$uv_dir/uv"
"$uv_dir/uv" python install "$python_version"
printf 'Installed pinned uv %s and Python %s at %s.\n' "$uv_version" "$python_version" "$uv_dir"
