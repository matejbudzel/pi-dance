import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pi_dance.songs import discover_songs


class SongDiscoveryTests(unittest.TestCase):
    def test_discovers_complete_bundles_sorted_by_title(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_song(root, "second", "Zebra")
            self._write_song(root, "first", "Apple")
            self._write_song(root, "broken", "Broken", audio=False)

            songs = discover_songs(root)

        self.assertEqual([song.title for song in songs], ["Apple", "Zebra"])

    @staticmethod
    def _write_song(root: Path, name: str, title: str, audio: bool = True) -> None:
        bundle = root / name
        bundle.mkdir()
        (bundle / "song.json").write_text(json.dumps({"title": title, "audio": "song.wav", "chart": "chart.sm"}))
        (bundle / "chart.sm").touch()
        if audio:
            (bundle / "song.wav").touch()
