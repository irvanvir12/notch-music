#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# The application selects native Wayland layer-shell or X11/XWayland.
exec /usr/bin/python3 notch_music.py "$@"
