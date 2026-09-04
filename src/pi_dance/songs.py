"""Discovery of prepared external song bundles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Song:
    title: str
    path: Path


def discover_songs(song_directory: Path) -> list[Song]:
    """Return valid prepared songs, sorted by their displayed title.

    A malformed or incomplete external bundle must not stop the game menu from
    opening, so invalid entries are ignored here.
    """
    if not song_directory.is_dir():
        return []

    songs: list[Song] = []
    for bundle in song_directory.iterdir():
        metadata_path = bundle / "song.json"
        if not bundle.is_dir() or not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            title = metadata["title"]
            audio = metadata["audio"]
            chart = metadata["chart"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            continue
        if not isinstance(title, str) or not title.strip():
            continue
        if not isinstance(audio, str) or not isinstance(chart, str):
            continue
        if not (bundle / audio).is_file() or not (bundle / chart).is_file():
            continue
        songs.append(Song(title=title.strip(), path=bundle))
    return sorted(songs, key=lambda song: song.title.casefold())
