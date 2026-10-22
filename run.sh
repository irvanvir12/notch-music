#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# XWayland supports explicit placement and keep-above on GNOME.
export GDK_BACKEND=x11
exec /usr/bin/python3 notch_music.py "$@"
