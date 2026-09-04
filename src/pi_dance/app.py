from __future__ import annotations

from enum import Enum, auto
import colorsys

import pygame

from .config import (
    APP_HEIGHT,
    APP_WIDTH,
    BACKGROUND,
    FONT_PATH,
    FOREGROUND,
    SONG_DIRECTORY,
    SETTINGS,
    TARGET_FPS,
    TITLE,
    WINDOW_TITLE,
)
from .input import Action, actions_from_event
from .songs import Song, discover_songs


class Screen(Enum):
    SPLASH = auto()
    SONG_LIST = auto()
    EXIT_CONFIRMATION = auto()


class App:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((APP_WIDTH, APP_HEIGHT))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.Font(FONT_PATH, 38)
        self.title_font.set_bold(True)
        self.list_font = pygame.font.Font(FONT_PATH, 28)
        self.question_font = pygame.font.Font(FONT_PATH, 28)
        self.question_font.set_bold(True)
        self.shrug_font = pygame.font.Font(FONT_PATH, 24)
        self.running = True
        self.current_screen = Screen.SPLASH
        self.songs: list[Song] = discover_songs(SONG_DIRECTORY)
        self.selected = 0
        self.first_visible_row = 0
        self.exit_confirmation_selected = False
        self.rainbow_title = self._make_rainbow_title()

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
            if self.current_screen is Screen.SPLASH:
                self.running = False
            elif self.current_screen is Screen.EXIT_CONFIRMATION:
                self.current_screen = Screen.SONG_LIST
            return
        if self.current_screen is Screen.SPLASH:
            if action is Action.START:
                self.current_screen = Screen.SONG_LIST
            return
        if self.current_screen is Screen.EXIT_CONFIRMATION:
            self._handle_exit_confirmation_action(action)
            return
        if action is Action.UP:
            self.selected = (self.selected - 1) % self._menu_item_count()
            self._scroll_selection_into_view()
        elif action is Action.DOWN:
            self.selected = (self.selected + 1) % self._menu_item_count()
            self._scroll_selection_into_view()
        elif action is Action.START and self.selected == len(self.songs):
            self.exit_confirmation_selected = False
            self.current_screen = Screen.EXIT_CONFIRMATION

    def _render(self) -> None:
        self.screen.fill(BACKGROUND)
        if self.current_screen is Screen.SPLASH:
            self._render_splash()
        elif self.current_screen is Screen.SONG_LIST:
            self._render_song_list()
        else:
            self._render_exit_confirmation()

    def _render_splash(self) -> None:
        title_position = self.rainbow_title.get_rect(center=(APP_WIDTH // 2, APP_HEIGHT // 2))
        self.screen.blit(self.rainbow_title, title_position)

    def _render_song_list(self) -> None:
        self.screen.blit(self.rainbow_title, (40, 28))
        if not self.songs:
            shrug = self.shrug_font.render(r"\_(^_^)_/", True, FOREGROUND)
            self.screen.blit(shrug, shrug.get_rect(center=(APP_WIDTH // 2, 240)))
            self._render_exit_item(APP_HEIGHT - 70)
            return

        for menu_row in range(self.first_visible_row, self.first_visible_row + self._visible_rows()):
            y = 118 + (menu_row - self.first_visible_row) * 44
            if menu_row < len(self.songs):
                song = self.songs[menu_row]
                color = song.focus_color if menu_row == self.selected else FOREGROUND
                if menu_row == self.selected:
                    chevron = self.list_font.render(">", True, color)
                    self.screen.blit(chevron, (64, y))
                title = self.list_font.render(song.title, True, color)
                self.screen.blit(title, (104, y))
            elif menu_row == len(self.songs) + 1:
                self._render_exit_item(y)

    def _render_exit_item(self, y: int) -> None:
        color = (255, 150, 100) if self.selected == len(self.songs) else FOREGROUND
        if self.selected == len(self.songs):
            chevron = self.list_font.render(">", True, color)
            self.screen.blit(chevron, (64, y))
        title = self.list_font.render(SETTINGS.exit_item_title, True, color)
        self.screen.blit(title, (104, y))

    def _render_exit_confirmation(self) -> None:
        self.screen.blit(self.rainbow_title, (40, 28))
        message = self.question_font.render(SETTINGS.exit_confirmation_text, True, FOREGROUND)
        self.screen.blit(message, message.get_rect(center=(APP_WIDTH // 2, 200)))

        self._render_confirmation_buttons()

    def _render_confirmation_buttons(self) -> None:
        buttons = (
            (SETTINGS.exit_confirm_button, self.exit_confirmation_selected),
            (SETTINGS.exit_cancel_button, not self.exit_confirmation_selected),
        )
        rendered = [
            (self.list_font.render(label, True, (255, 150, 100) if selected else FOREGROUND), selected)
            for label, selected in buttons
        ]
        gap = 72
        x = (APP_WIDTH - sum(text.get_width() for text, _ in rendered) - gap) // 2
        for text, selected in rendered:
            self.screen.blit(text, (x, 286))
            if selected:
                chevron = self.list_font.render(">", True, (255, 150, 100))
                self.screen.blit(chevron, (x - 34, 286))
            x += text.get_width() + gap

    def _handle_exit_confirmation_action(self, action: Action) -> None:
        if action in (Action.LEFT, Action.RIGHT, Action.UP, Action.DOWN):
            self.exit_confirmation_selected = not self.exit_confirmation_selected
        elif action is Action.START:
            if self.exit_confirmation_selected:
                self.running = False
            else:
                self.current_screen = Screen.SONG_LIST

    def _visible_rows(self) -> int:
        return (APP_HEIGHT - 118 - 30) // 44

    def _menu_item_count(self) -> int:
        return len(self.songs) + 1

    def _selected_menu_row(self) -> int:
        return self.selected if self.selected < len(self.songs) else len(self.songs) + 1

    def _scroll_selection_into_view(self) -> None:
        visible_rows = self._visible_rows()
        selected_row = self._selected_menu_row()
        if selected_row < self.first_visible_row:
            self.first_visible_row = selected_row
        elif selected_row >= self.first_visible_row + visible_rows:
            self.first_visible_row = selected_row - visible_rows + 1

    def _make_rainbow_title(self) -> pygame.Surface:
        mask = self.title_font.render(TITLE, True, FOREGROUND)
        rainbow = pygame.Surface(mask.get_size(), pygame.SRCALPHA)
        stripe_width = 12
        for stripe, x in enumerate(range(-mask.get_height(), mask.get_width() + mask.get_height(), stripe_width)):
            color = colorsys.hsv_to_rgb((stripe % 12) / 12, 0.85, 1.0)
            pygame.draw.polygon(
                rainbow,
                tuple(round(channel * 255) for channel in color),
                ((x, 0), (x + stripe_width, 0), (x + stripe_width + mask.get_height(), mask.get_height()), (x + mask.get_height(), mask.get_height())),
            )
        rainbow.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return rainbow
