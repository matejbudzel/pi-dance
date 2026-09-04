import unittest

from pi_dance.charts import parse_sm


SM = """
#OFFSET:1.0;
#BPMS:0.0=120.0,4.0=60.0;
#NOTES:
     dance-single:
     :
     Beginner:
     1:
     0:
1000
0100
0010
0001
,
1000
0000
0000
0000
;
#NOTES:
     dance-single:
     :
     Hard:
     8:
     0:
0000
0001
0000
0000
;
"""


class StepManiaChartTests(unittest.TestCase):
    def test_returns_every_dance_single_chart(self) -> None:
        charts = parse_sm(SM)

        self.assertEqual([chart.difficulty for chart in charts.charts], ["Beginner", "Hard"])
        self.assertEqual([chart.meter for chart in charts.charts], [1, 8])

    def test_converts_rows_and_bpm_changes_to_absolute_timestamps(self) -> None:
        beginner = parse_sm(SM).charts[0]

        self.assertEqual([note.direction for note in beginner.notes], ["left", "down", "up", "right", "left"])
        self.assertEqual([note.timestamp for note in beginner.notes], [1.0, 1.5, 2.0, 2.5, 3.0])

    def test_ignores_non_tap_notes_for_the_mvp(self) -> None:
        charts = parse_sm("#BPMS:0=120; #NOTES:dance-single::Easy:2:0:2000\n3000\n4000\nM000;")

        self.assertEqual(charts.charts[0].notes, ())
