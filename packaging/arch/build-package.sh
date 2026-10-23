#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$project_dir/packaging/arch"
/usr/bin/python - "$project_dir" <<'PY'
import sys
import tarfile
from pathlib import Path
root = Path(sys.argv[1])
version = root.joinpath('VERSION').read_text().strip()
with tarfile.open(f'notch-music-{version}.tar.gz', 'w:gz') as archive:
    for name in ('notch_music.py', 'metadata.py', 'playlists.py', 'selection.py', 'themes.py', 'desktop_support.py',
                 'README.md', 'assets', 'packaging/notch-music.desktop', 'tests'):
        archive.add(root / name, arcname=f'notch-music-{version}/{name}',
                    filter=lambda info: None if '__pycache__' in info.name or info.name.endswith('.pyc') else info)
PY
if [[ "${NOTCH_BUILD_ONLY:-0}" == 1 ]]; then
    exec makepkg "$@"
fi
exec makepkg -si "$@"
