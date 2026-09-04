"""Application state coordination and action handling."""

from __future__ import annotations

from enum import Enum, auto
from contextlib import nullcontext

import pygame

from .assets import Assets
from .charts import Chart, load_sm
from .config import APP_HEIGHT, APP_WIDTH, BACKGROUND, SETTINGS, SONG_DIRECTORY, TARGET_FPS, WINDOW_TITLE
from .gameplay import JudgedNote, Judgement, Session
from .fbdev import FbdevPresenter
from .console_input import ConsoleInput
from .input import Action, actions_from_event
from .songs import Song, discover_songs
from . import views


class Screen(Enum):
    SPLASH = auto()
    SONG_LIST = auto()
    EXIT_CONFIRMATION = auto()
    COUNTDOWN = auto()
    PLAYING = auto()
    PAUSED = auto()
    SONG_EXIT_CONFIRMATION = auto()
    RESULT = auto()


COUNTDOWN_SECONDS = 3
FEEDBACK_DURATION_SECONDS = 0.45
RECEPTOR_GLOW_DURATION_MS = 110

ACTION_DIRECTIONS = {
    Action.LEFT: "left",
    Action.DOWN: "down",
    Action.UP: "up",
    Action.RIGHT: "right",
}
DEBUG_RESULT_STARS = {
    Action.DEBUG_RESULT_1: 1,
    Action.DEBUG_RESULT_2: 2,
    Action.DEBUG_RESULT_3: 3,
    Action.DEBUG_RESULT_4: 4,
    Action.DEBUG_RESULT_5: 5,
}


class App:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((APP_WIDTH, APP_HEIGHT))
        self.framebuffer = self._open_framebuffer_presenter()
        self.clock = pygame.time.Clock()
        self.running = True
        self.current_screen = Screen.SPLASH
        self.songs: list[Song] = discover_songs(SONG_DIRECTORY)
        self.assets = Assets(self.songs)
        self.selected = 0
        self.first_visible_row = 0
        self.exit_confirmation_selected = False
        self.song_exit_confirmation_selected = False
        self.song_exit_return_screen = Screen.COUNTDOWN
        self.countdown_remaining_on_modal = 0
        self.active_song: Song | None = None
        self.active_chart: Chart | None = None
        self.session: Session | None = None
        self.feedback: Judgement | None = None
        self.feedback_until = 0.0
        self.receptor_glow_until = {direction: 0 for direction in ACTION_DIRECTIONS.values()}
        self.playback_started = False
        self.result_started_at = 0
        self.result_stars = 0
        self.countdown_started_at = 0
        self.show_performance_hud = False

    def run(self) -> None:
        console_input = ConsoleInput() if self.framebuffer is not None else None
        try:
            with console_input or nullcontext():
                self.console_input = console_input
                while self.running:
                    self._handle_events()
                    self._update()
                    self._render()
                    pygame.display.flip()
                    if self.framebuffer is not None:
                        self.framebuffer.present(self.screen)
                    self.clock.tick(TARGET_FPS)
        finally:
            pygame.mixer.music.stop()
            if self.framebuffer is not None:
                self.framebuffer.close()
            pygame.quit()

    @staticmethod
    def _open_framebuffer_presenter() -> FbdevPresenter | None:
        if SETTINGS.display_backend == "pygame":
            return None
        if SETTINGS.display_backend == "fbdev":
            return FbdevPresenter(SETTINGS.framebuffer_device, (APP_WIDTH, APP_HEIGHT))
        raise ValueError(f"unknown display backend: {SETTINGS.display_backend}")

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            for action in actions_from_event(event):
                self._handle_action(action)
        if getattr(self, "console_input", None) is not None:
            for action in self.console_input.poll_actions():
                self._handle_action(action)

    def _handle_action(self, action: Action) -> None:
        if action is Action.DEBUG_TOGGLE_PERFORMANCE:
            self.show_performance_hud = not self.show_performance_hud
        elif action in DEBUG_RESULT_STARS and self.current_screen in (Screen.COUNTDOWN, Screen.PLAYING, Screen.PAUSED):
            self._show_debug_result(DEBUG_RESULT_STARS[action])
        elif action is Action.SELECT:
            self._handle_select()
        elif self.current_screen is Screen.SPLASH and action is Action.START:
            self.current_screen = Screen.SONG_LIST
        elif self.current_screen is Screen.SONG_LIST:
            self._handle_song_list_action(action)
        elif self.current_screen is Screen.EXIT_CONFIRMATION:
            self._handle_application_exit_action(action)
        elif self.current_screen is Screen.PLAYING and action is Action.START:
            pygame.mixer.music.pause()
            self.current_screen = Screen.PAUSED
        elif self.current_screen in (Screen.COUNTDOWN, Screen.PLAYING) and action in ACTION_DIRECTIONS:
            self._handle_direction(ACTION_DIRECTIONS[action])
        elif self.current_screen is Screen.PAUSED and action is Action.START:
            pygame.mixer.music.unpause()
            self.current_screen = Screen.PLAYING
        elif self.current_screen is Screen.SONG_EXIT_CONFIRMATION:
            self._handle_song_exit_action(action)
        elif self.current_screen is Screen.RESULT and action is Action.START:
            self._stop_song()
            self.current_screen = Screen.SONG_LIST

    def _handle_select(self) -> None:
        if self.current_screen is Screen.SPLASH:
            self.running = False
        elif self.current_screen is Screen.EXIT_CONFIRMATION:
            self.current_screen = Screen.SONG_LIST
        elif self.current_screen is Screen.SONG_EXIT_CONFIRMATION:
            self._cancel_song_exit()
        elif self.current_screen is Screen.RESULT:
            self._stop_song()
            self.current_screen = Screen.SONG_LIST
        elif self.current_screen in (Screen.COUNTDOWN, Screen.PLAYING, Screen.PAUSED):
            self.song_exit_return_screen = self.current_screen
            if self.current_screen is Screen.COUNTDOWN:
                self.countdown_remaining_on_modal = self._countdown_remaining()
            elif self.current_screen is Screen.PLAYING:
                pygame.mixer.music.pause()
            self.song_exit_confirmation_selected = False
            self.current_screen = Screen.SONG_EXIT_CONFIRMATION

    def _handle_song_list_action(self, action: Action) -> None:
        if action is Action.UP:
            self.selected = (self.selected - 1) % self._menu_item_count()
            self._scroll_selection_into_view()
        elif action is Action.DOWN:
            self.selected = (self.selected + 1) % self._menu_item_count()
            self._scroll_selection_into_view()
        elif action is Action.START:
            if self.selected == len(self.songs):
                self.exit_confirmation_selected = False
                self.current_screen = Screen.EXIT_CONFIRMATION
            else:
                self._prepare_song(self.songs[self.selected])

    def _handle_application_exit_action(self, action: Action) -> None:
        if action in (Action.LEFT, Action.RIGHT, Action.UP, Action.DOWN):
            self.exit_confirmation_selected = not self.exit_confirmation_selected
        elif action is Action.START:
            self.running = not self.exit_confirmation_selected
            if self.running:
                self.current_screen = Screen.SONG_LIST

    def _handle_song_exit_action(self, action: Action) -> None:
        if action in (Action.LEFT, Action.RIGHT, Action.UP, Action.DOWN):
            self.song_exit_confirmation_selected = not self.song_exit_confirmation_selected
        elif action is Action.START:
            if self.song_exit_confirmation_selected:
                self._stop_song()
                self.current_screen = Screen.SONG_LIST
            else:
                self._cancel_song_exit()

    def _handle_direction(self, direction: str) -> None:
        self.receptor_glow_until[direction] = pygame.time.get_ticks() + RECEPTOR_GLOW_DURATION_MS
        if self.current_screen is Screen.PLAYING and self.session is not None:
            result = self.session.press(direction, self._song_position_seconds())
            self._show_feedback(Judgement.MISS if result is None else result.judgement)

    def _prepare_song(self, song: Song) -> None:
        try:
            parsed = load_sm(song.chart_path)
            self.active_chart = next(chart for chart in parsed.charts if chart.difficulty == song.chart_difficulty and chart.meter == song.chart_meter)
            pygame.mixer.music.load(str(song.audio_path))
        except (OSError, pygame.error, StopIteration, ValueError):
            return
        self.active_song = song
        self.session = Session(self.active_chart.notes)
        self.feedback = None
        self.playback_started = False
        self.countdown_started_at = pygame.time.get_ticks()
        self.current_screen = Screen.COUNTDOWN

    def _update(self) -> None:
        if self.current_screen is Screen.COUNTDOWN and self._countdown_remaining() <= 0:
            pygame.mixer.music.play()
            self.playback_started = True
            self.current_screen = Screen.PLAYING
        elif self.current_screen is Screen.PLAYING and self.session is not None:
            song_time = self._song_position_seconds()
            for result in self.session.expire(song_time):
                self._show_feedback(result.judgement)
            if self.playback_started and not pygame.mixer.music.get_busy():
                self.session.expire(float("inf"))
                pygame.mixer.music.stop()
                self.result_stars = self.session.stars()
                self.result_started_at = pygame.time.get_ticks()
                self.current_screen = Screen.RESULT

    def _cancel_song_exit(self) -> None:
        if self.song_exit_return_screen is Screen.COUNTDOWN:
            self.countdown_started_at = pygame.time.get_ticks() - (COUNTDOWN_SECONDS - self.countdown_remaining_on_modal) * 1000
        elif self.song_exit_return_screen is Screen.PLAYING:
            pygame.mixer.music.unpause()
        self.current_screen = self.song_exit_return_screen

    def _stop_song(self) -> None:
        pygame.mixer.music.stop()
        self.active_song = None
        self.active_chart = None
        self.session = None
        self.feedback = None
        self.playback_started = False
        self.result_stars = 0

    def _show_debug_result(self, stars: int) -> None:
        pygame.mixer.music.stop()
        self.result_stars = stars
        self.result_started_at = pygame.time.get_ticks()
        self.current_screen = Screen.RESULT

    def _render(self) -> None:
        self.screen.fill(BACKGROUND)
        now_ms = pygame.time.get_ticks()
        if self.current_screen is Screen.SPLASH:
            views.render_splash(self.screen, self.assets)
        elif self.current_screen is Screen.SONG_LIST:
            views.render_song_list(self.screen, self.assets, self.songs, self.selected, self.first_visible_row, self._visible_rows())
        elif self.current_screen is Screen.EXIT_CONFIRMATION:
            views.render_application_exit_confirmation(self.screen, self.assets, self.exit_confirmation_selected)
        elif self.current_screen is Screen.RESULT:
            views.render_result(self.screen, self.assets, self.active_song, self._audio_position_seconds(), self.result_stars, self.result_started_at, now_ms)
        else:
            views.render_gameplay(self.screen, self.assets, self.active_song, self.session, self._audio_position_seconds(), self._song_position_seconds(), self.feedback, self.feedback_until, self.receptor_glow_until, now_ms)
            if self.current_screen is Screen.COUNTDOWN:
                views.render_countdown(self.screen, self.assets, self._countdown_remaining())
            elif self.current_screen is Screen.PAUSED:
                views.render_modal(self.screen, self.assets, SETTINGS.pause_text)
            elif self.current_screen is Screen.SONG_EXIT_CONFIRMATION:
                views.render_song_exit_confirmation(self.screen, self.assets, self.song_exit_confirmation_selected)
        if self.show_performance_hud:
            views.render_performance_hud(self.screen, self.assets, self.clock.get_fps(), self.clock.get_time())

    def _song_position_seconds(self) -> float:
        return self._audio_position_seconds() + SETTINGS.timing_offset_ms / 1000

    def _audio_position_seconds(self) -> float:
        return 0.0 if self.current_screen is Screen.COUNTDOWN else max(0, pygame.mixer.music.get_pos()) / 1000

    def _show_feedback(self, judgement: Judgement) -> None:
        self.feedback = judgement
        self.feedback_until = self._song_position_seconds() + FEEDBACK_DURATION_SECONDS

    def _countdown_remaining(self) -> int:
        return max(0, COUNTDOWN_SECONDS - int((pygame.time.get_ticks() - self.countdown_started_at) / 1000))

    def _visible_rows(self) -> int:
        return (APP_HEIGHT - 118 - 30) // 44

    def _menu_item_count(self) -> int:
        return len(self.songs) + 1

    def _scroll_selection_into_view(self) -> None:
        selected_row = self.selected if self.selected < len(self.songs) else len(self.songs) + 1
        if selected_row < self.first_visible_row:
            self.first_visible_row = selected_row
        elif selected_row >= self.first_visible_row + self._visible_rows():
            self.first_visible_row = selected_row - self._visible_rows() + 1
