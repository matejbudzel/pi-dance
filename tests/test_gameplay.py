import unittest

from pi_dance.charts import Note
from pi_dance.gameplay import Judgement, Session


class SessionTests(unittest.TestCase):
    def test_judges_directional_notes_using_audio_time(self) -> None:
        session = Session((Note(1.0, "left"), Note(1.2, "right")))

        judgement = session.press("left", 1.08)

        self.assertIsNotNone(judgement)
        self.assertIs(judgement.judgement, Judgement.GREAT)
        self.assertEqual(len(session.pending), 1)

    def test_accepts_a_more_forgiving_ok_timing_window(self) -> None:
        session = Session((Note(1.0, "left"),))

        judgement = session.press("left", 1.26)

        self.assertIsNotNone(judgement)
        self.assertIs(judgement.judgement, Judgement.OK)

    def test_ignores_a_bounce_after_a_successful_hit(self) -> None:
        session = Session((Note(1.0, "left"),))

        session.press("left", 1.0)
        bounce = session.press("left", 1.06)

        self.assertIsNone(bounce)
        self.assertTrue(session.last_press_was_ignored)
        self.assertEqual(len(session.judgements), 1)

    def test_keeps_very_close_chart_notes_playable(self) -> None:
        session = Session((Note(1.0, "left"), Note(1.12, "right")))

        session.press("left", 1.0)
        close_note = session.press("right", 1.12)

        self.assertIsNotNone(close_note)
        self.assertFalse(session.last_press_was_ignored)

    def test_late_notes_become_misses(self) -> None:
        session = Session((Note(1.0, "left"), Note(2.0, "up")))

        misses = session.expire(1.29)

        self.assertEqual([result.judgement for result in misses], [Judgement.MISS])
        self.assertEqual([note.direction for note in session.pending], ["up"])

    def test_stars_are_always_at_least_one(self) -> None:
        session = Session((Note(1.0, "left"),))
        session.expire(2.0)

        self.assertEqual(session.stars(), 1)

    def test_perfect_song_earns_five_stars(self) -> None:
        session = Session((Note(1.0, "left"), Note(2.0, "up")))
        session.press("left", 1.0)
        session.press("up", 2.0)

        self.assertEqual(session.stars(), 5)
