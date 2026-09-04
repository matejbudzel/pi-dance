import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pi_dance.songs import discover_songs, focus_color_for_title


class SongDiscoveryTests(unittest.TestCase):
    def test_discovers_complete_bundles_sorted_by_title(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_song(root, "second", "Zebra")
            self._write_song(root, "first", "Apple")
            self._write_song(root, "broken", "Broken", audio=False)

            songs = discover_songs(root)

        self.assertEqual([song.title for song in songs], ["Apple", "Zebra"])

    def test_focus_color_is_stable_and_bright(self) -> None:
        color = focus_color_for_title("How Far I'll Go")

        self.assertEqual(color, focus_color_for_title("How Far I'll Go"))
        self.assertNotEqual(color, focus_color_for_title("Shake It Off"))
        self.assertGreaterEqual(max(color), 230)

    @staticmethod
    def _write_song(root: Path, name: str, title: str, audio: bool = True) -> None:
        bundle = root / name
        bundle.mkdir()
        (bundle / "song.json").write_text(json.dumps({
            "title": title,
            "audio": "song.wav",
            "chart": "chart.sm",
            "duration_seconds": 120,
            "chart_difficulty": "Beginner",
            "chart_meter": 1,
        }))
        (bundle / "chart.sm").touch()
        if audio:
            (bundle / "song.wav").touch()
