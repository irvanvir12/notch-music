#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bundle="$project_dir/dist/Notch-Music-Windows-fixed"
if [[ ! -f "$bundle/runtime/bin/python.exe" ]]; then
    echo 'Paket Windows belum tersedia di dist/Notch-Music-Windows-fixed.' >&2
    exit 1
fi
bootstrap="$bundle/app/bootstrap.py"
if command -v wslpath >/dev/null 2>&1; then
    bootstrap="$(wslpath -w "$bootstrap")"
elif command -v cygpath >/dev/null 2>&1; then
    bootstrap="$(cygpath -w "$bootstrap")"
fi
exec "$bundle/runtime/bin/python.exe" "$bootstrap" "$@"
