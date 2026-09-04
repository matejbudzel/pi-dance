import os
from pathlib import Path
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame


ASSET_DIRECTORY = Path(__file__).parents[1] / "src" / "pi_dance" / "assets" / "gameplay"


class GameplayAssetTests(unittest.TestCase):
    def test_all_temporary_gameplay_sprites_are_32_pixels_square(self) -> None:
        for name in ("arrow.png", "arrow-flow.png", "heart.png", "thumb.png", "shrug.png"):
            with self.subTest(name=name):
                self.assertEqual(pygame.image.load(ASSET_DIRECTORY / name).get_size(), (32, 32))
