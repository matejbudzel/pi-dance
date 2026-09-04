import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from pi_dance.app import App, Screen
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
