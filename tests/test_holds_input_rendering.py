import os
from pathlib import Path
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from pi_dance.app import App, Screen
from pi_dance.charts import Note
from pi_dance.gameplay import Judgement, Session
from pi_dance.input import Action, Release, actions_from_event
from pi_dance.songs import Song, fallback_cover_path
from pi_dance import views


class HoldInputRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = App()

    def tearDown(self) -> None:
        pygame.quit()

    def test_keyboard_and_pad_share_press_and_release_actions(self) -> None:
        for down, up, fields in ((pygame.KEYDOWN, pygame.KEYUP, {"key": pygame.K_LEFT}),
                                 (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, {"button": 0})):
            self.assertEqual(actions_from_event(pygame.event.Event(down, **fields)), [Action.LEFT])
            self.assertEqual(actions_from_event(pygame.event.Event(up, **fields)), [Release(Action.LEFT)])
        self.assertEqual(actions_from_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN)), [])

    def test_release_action_finishes_active_hold(self) -> None:
        self.app.current_screen = Screen.PLAYING
        self.app.session = Session((Note(0, "left", 10),))
        self.app._handle_action(Action.LEFT)
        self.app._handle_action(Release(Action.LEFT))
        self.assertEqual(self.app.session.active_holds, {})
        self.assertIs(self.app.feedback, Judgement.MISS)

    def test_cached_render_matches_full_render_for_moving_and_held_tails(self) -> None:
        song = Song("Example", Path("."), (255, 100, 150), Path("song.wav"),
                    Path("chart.sm"), fallback_cover_path(), 30, "Easy", 2)
        self.app.assets.covers[song.path] = pygame.image.load(fallback_cover_path()).convert()
        session = Session((Note(1, "left", 3), Note(1, "right", 30)))
        base = views.create_gameplay_base(self.app.screen, self.app.assets, song)
        cached = base.copy()
        full = base.copy()
        previous = []
        for time in (0, 0.5, 1, 1.5, 2.9, 3):
            if time == 1:
                session.press("left", time)
                session.press("right", time)
            session.expire(time)
            arguments = (self.app.assets, song, session, time, time, None, 0,
                         self.app.receptor_glow_until, 10000)
            full.fill((0, 0, 0))
            views.render_gameplay(full, *arguments)
            previous, _ = views.render_cached_gameplay(cached, base, *arguments, None, previous)
            self.assertEqual(pygame.image.tobytes(cached, "RGB"), pygame.image.tobytes(full, "RGB"), time)
