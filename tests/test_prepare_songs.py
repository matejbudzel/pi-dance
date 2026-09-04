from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "prepare_songs.py"
SPEC = spec_from_file_location("prepare_songs", MODULE_PATH)
assert SPEC and SPEC.loader
prepare_songs = module_from_spec(SPEC)
sys.modules[SPEC.name] = prepare_songs
SPEC.loader.exec_module(prepare_songs)


class PrepareSongsTests(unittest.TestCase):
    def test_selects_beginner_chart(self) -> None:
        contents = """
#NOTES:dance-single::Hard:8:0:0000;
#NOTES:dance-single::Beginner:3:0:0000;
#NOTES:dance-double::Beginner:1:0:00000000;
"""
        self.assertEqual(prepare_songs.easiest_dance_single(contents), prepare_songs.ChartChoice("Beginner", 3))

    def test_uses_meter_when_difficulty_names_match(self) -> None:
        contents = "#NOTES:dance-single::Easy:5:0:0000; #NOTES:dance-single::Easy:2:0:0000;"
        self.assertEqual(prepare_songs.easiest_dance_single(contents), prepare_songs.ChartChoice("Easy", 2))

    def test_reads_a_basic_sm_tag(self) -> None:
        self.assertEqual(prepare_songs.sm_tag("#TITLE:Example Song;", "TITLE"), "Example Song")
