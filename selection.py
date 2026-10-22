"""Resolve the file chooser's Select action without requiring a selection."""
from pathlib import Path

AUDIO = {'.mp3', '.flac', '.ogg', '.opus', '.wav', '.m4a', '.aac', '.wma'}


def resolve_selection(filenames, current_folder):
    paths = [Path(name) for name in filenames]
    songs = [p for p in paths if p.is_file() and p.suffix.lower() in AUDIO]
    folders = [p for p in paths if p.is_dir()]
    if songs:
        return songs, folders
    return [], folders or ([Path(current_folder)] if current_folder else [])
