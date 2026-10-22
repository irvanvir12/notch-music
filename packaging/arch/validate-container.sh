#!/usr/bin/env bash
# Run as root inside a disposable Arch Linux container, not on the host.
set -euo pipefail
if [[ ! -f /.dockerenv ]] || [[ ! -f /etc/arch-release ]]; then
    echo 'This checker must run inside an Arch Linux Docker container.' >&2
    exit 1
fi
project_dir=${1:?Pass the checked-out source directory}
pacman -Syu --noconfirm --needed python python-gobject python-cairo gtk3 gtk-layer-shell \
    gstreamer gst-plugins-base gst-plugins-good gst-libav adwaita-icon-theme
build_dir=$(mktemp -d /tmp/notch-arch-build.XXXXXX)
cp "$project_dir"/*.py "$project_dir/README.md" "$project_dir/VERSION" "$build_dir/"
cp -r "$project_dir/assets" "$project_dir/tests" "$project_dir/packaging" "$build_dir/"
useradd -m notchbuilder
chown -R notchbuilder:notchbuilder "$build_dir"
su notchbuilder -s /bin/bash -c "cd '$build_dir/packaging/arch' && NOTCH_BUILD_ONLY=1 ./build-package.sh --noconfirm"
pacman -U --noconfirm "$build_dir"/packaging/arch/notch-music-*.pkg.tar.zst
/usr/bin/python - <<'PY'
import sys
sys.path.insert(0, '/usr/lib/notch-music')
import gi
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import GtkLayerShell
from notch_music import Notch
from metadata import parse_lyrics
from desktop_support import choose_backend
assert choose_backend({'XDG_CURRENT_DESKTOP': 'KDE', 'WAYLAND_DISPLAY': 'wayland-0'}, True) == 'wayland,x11'
assert parse_lyrics('[00:01.00]Hello')[0] == [(1., 'Hello')]
print('Arch native installation/import checks OK')
PY
if [[ -d /out ]]; then
    cp "$build_dir"/packaging/arch/notch-music-*.pkg.tar.zst /out/
fi
