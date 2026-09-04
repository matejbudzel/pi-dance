import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from pi_dance.app import App, Screen
from pi_dance.gameplay import Judgement, Session
from pi_dance.charts import Note
from pi_dance.input import Action


class ExitConfirmationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = App()
        self.app.current_screen = Screen.EXIT_CONFIRMATION

    def tearDown(self) -> None:
        pygame.quit()

    def test_cancel_returns_to_the_song_list(self) -> None:
        self.app.exit_confirmation_selected = False

        self.app._handle_action(Action.START)

        self.assertTrue(self.app.running)
        self.assertIs(self.app.current_screen, Screen.SONG_LIST)

    def test_confirm_stops_the_application(self) -> None:
        self.app.exit_confirmation_selected = True

        self.app._handle_action(Action.START)

        self.assertFalse(self.app.running)

    def test_song_exit_cancel_resumes_playback(self) -> None:
        self.app.current_screen = Screen.PLAYING

        with patch("pi_dance.app.pygame.mixer.music.pause") as pause, patch("pi_dance.app.pygame.mixer.music.unpause") as unpause:
            self.app._handle_action(Action.SELECT)
            self.app._handle_action(Action.START)

        pause.assert_called_once()
        unpause.assert_called_once()
        self.assertIs(self.app.current_screen, Screen.PLAYING)

    def test_unmatched_direction_shows_shrug_without_a_score_judgement(self) -> None:
        self.app.current_screen = Screen.PLAYING
        self.app.session = Session((Note(10.0, "up"),))

        self.app._handle_action(Action.LEFT)

        self.assertIs(self.app.feedback, Judgement.MISS)
        self.assertEqual(self.app.session.judgements, [])
        self.assertGreater(self.app.receptor_glow_until["left"], pygame.time.get_ticks())

    def test_debug_result_key_opens_requested_star_result(self) -> None:
        self.app.current_screen = Screen.PLAYING

        with patch("pi_dance.app.pygame.mixer.music.stop") as stop:
            self.app._handle_action(Action.DEBUG_RESULT_4)

        stop.assert_called_once()
        self.assertIs(self.app.current_screen, Screen.RESULT)
        self.assertEqual(self.app.result_stars, 4)
