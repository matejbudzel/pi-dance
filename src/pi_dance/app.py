from __future__ import annotations

import pygame

from .config import ACCENT, APP_HEIGHT, APP_WIDTH, BACKGROUND, FOREGROUND, TARGET_FPS, WINDOW_TITLE
from .input import Action, actions_from_event


class App:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((APP_WIDTH, APP_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 28)
        self.running = True
        self.selected = 0
        self.demo_songs = ["NO SONGS FOUND", "ADD SONG BUNDLES", "TO CONFIGURED PATH"]

    def run(self) -> None:
        while self.running:
            self._handle_events()
            self._render()
            pygame.display.flip()
            self.clock.tick(TARGET_FPS)

        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            for action in actions_from_event(event):
                self._handle_action(action)

    def _handle_action(self, action: Action) -> None:
        if action is Action.SELECT:
            self.running = False
        elif action is Action.UP:
            self.selected = (self.selected - 1) % len(self.demo_songs)
        elif action is Action.DOWN:
            self.selected = (self.selected + 1) % len(self.demo_songs)

    def _render(self) -> None:
        self.screen.fill(BACKGROUND)

        title = self.font.render("PI-DANCE", True, ACCENT)
        self.screen.blit(title, (40, 32))

        subtitle = self.small_font.render("UP/DOWN select   ENTER/SPACE start   ESC back", True, FOREGROUND)
        self.screen.blit(subtitle, (40, 88))

        y = 170
        for index, song in enumerate(self.demo_songs):
            prefix = "> " if index == self.selected else "  "
            color = ACCENT if index == self.selected else FOREGROUND
            row = self.font.render(prefix + song, True, color)
            self.screen.blit(row, (72, y))
            y += 64
