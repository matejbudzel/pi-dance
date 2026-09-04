from __future__ import annotations

import colorsys
from enum import Enum, auto

import pygame

from .charts import Chart, load_sm
from .config import APP_HEIGHT, APP_WIDTH, BACKGROUND, FONT_PATH, FOREGROUND, SETTINGS, SONG_DIRECTORY, TARGET_FPS, TITLE, WINDOW_TITLE
from .gameplay import JudgedNote, Judgement, Session
from .input import Action, actions_from_event
from .songs import Song, discover_songs


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
NOTE_TRAVEL_SECONDS = 2.0
FEEDBACK_DURATION_SECONDS = 0.45
RECEPTOR_GLOW_DURATION_MS = 110
STAR_DELAY_MS = 500

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
        self.rainbow_title = self._make_rainbow_title()
        self.receptors = self._load_receptors()
        self.flow_arrows = self._load_flow_arrows()
        self.receptor_glows = {direction: pygame.transform.scale(arrow, (42, 42)) for direction, arrow in self.flow_arrows.items()}
        self.feedback_icons = self._load_feedback_icons()
        self.draft_star, self.earned_star = self._load_result_stars()

    def run(self) -> None:
        while self.running:
            self._handle_events()
            self._update()
            self._render()
            pygame.display.flip()
            self.clock.tick(TARGET_FPS)
        pygame.mixer.music.stop()
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            for action in actions_from_event(event):
                self._handle_action(action)

    def _handle_action(self, action: Action) -> None:
        if action in DEBUG_RESULT_STARS and self.current_screen in (Screen.COUNTDOWN, Screen.PLAYING, Screen.PAUSED):
            self._show_debug_result(DEBUG_RESULT_STARS[action])
            return
        if action is Action.SELECT:
            self._handle_select()
            return
        if self.current_screen is Screen.SPLASH:
            if action is Action.START:
                self.current_screen = Screen.SONG_LIST
        elif self.current_screen is Screen.SONG_LIST:
            self._handle_song_list_action(action)
        elif self.current_screen is Screen.EXIT_CONFIRMATION:
            self._handle_application_exit_action(action)
        elif self.current_screen is Screen.PLAYING and action is Action.START:
            pygame.mixer.music.pause()
            self.current_screen = Screen.PAUSED
        elif self.current_screen in (Screen.COUNTDOWN, Screen.PLAYING) and action in ACTION_DIRECTIONS:
            direction = ACTION_DIRECTIONS[action]
            self.receptor_glow_until[direction] = pygame.time.get_ticks() + RECEPTOR_GLOW_DURATION_MS
            if self.current_screen is Screen.PLAYING and self.session is not None:
                result = self.session.press(direction, self._song_position_seconds())
                if result is None:
                    self._show_feedback(Judgement.MISS)
                else:
                    self._show_judgement(result)
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
            if self.exit_confirmation_selected:
                self.running = False
            else:
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
                self._show_judgement(result)
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
        if self.current_screen is Screen.SPLASH:
            self._render_splash()
        elif self.current_screen is Screen.SONG_LIST:
            self._render_song_list()
        elif self.current_screen is Screen.EXIT_CONFIRMATION:
            self._render_application_exit_confirmation()
        elif self.current_screen is Screen.RESULT:
            self._render_result()
        else:
            self._render_gameplay()
            if self.current_screen is Screen.COUNTDOWN:
                self._render_countdown()
            elif self.current_screen is Screen.PAUSED:
                self._render_modal(SETTINGS.pause_text)
            elif self.current_screen is Screen.SONG_EXIT_CONFIRMATION:
                self._render_song_exit_confirmation()

    def _render_splash(self) -> None:
        self.screen.blit(self.rainbow_title, self.rainbow_title.get_rect(center=(APP_WIDTH // 2, APP_HEIGHT // 2)))

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
                    self._blit_chevron(64, y, color)
                self.screen.blit(self.list_font.render(song.title, True, color), (104, y))
            elif menu_row == len(self.songs) + 1:
                self._render_exit_item(y)

    def _render_exit_item(self, y: int) -> None:
        color = (255, 150, 100) if self.selected == len(self.songs) else FOREGROUND
        if self.selected == len(self.songs):
            self._blit_chevron(64, y, color)
        self.screen.blit(self.list_font.render(SETTINGS.exit_item_title, True, color), (104, y))

    def _render_application_exit_confirmation(self) -> None:
        self.screen.blit(self.rainbow_title, (40, 28))
        message = self.question_font.render(SETTINGS.exit_confirmation_text, True, FOREGROUND)
        self.screen.blit(message, message.get_rect(center=(APP_WIDTH // 2, 200)))
        self._render_confirmation_buttons(SETTINGS.exit_confirm_button, SETTINGS.exit_cancel_button, self.exit_confirmation_selected, 286)

    def _render_gameplay(self) -> None:
        self._render_gameplay_header()
        self._render_flowing_notes()
        for index, direction in enumerate(("left", "down", "up", "right")):
            receptor = self.receptors[direction]
            center = (APP_WIDTH // 2 - 142 + index * 84, 132)
            if pygame.time.get_ticks() <= self.receptor_glow_until[direction]:
                glow = self.receptor_glows[direction]
                self.screen.blit(glow, glow.get_rect(center=center))
            self.screen.blit(receptor, receptor.get_rect(center=center))
        self._render_feedback()

    def _render_gameplay_header(self) -> None:
        if self.active_song is None:
            return
        header_color = tuple(channel * 55 // 100 for channel in self.active_song.focus_color)
        pygame.draw.rect(self.screen, header_color, pygame.Rect(0, 0, APP_WIDTH, 92))
        self._render_progress_bar()
        title = self.list_font.render(self.active_song.title, True, FOREGROUND)
        self.screen.blit(title, (40, 42))

    def _render_progress_bar(self) -> None:
        rect = pygame.Rect(40, 16, APP_WIDTH - 80, 12)
        pygame.draw.rect(self.screen, FOREGROUND, rect, width=2)
        if self.active_song is not None:
            ratio = min(1.0, self._audio_position_seconds() / self.active_song.duration_seconds)
            if ratio > 0:
                fill = rect.copy()
                fill.width = max(1, round(rect.width * ratio))
                pygame.draw.rect(self.screen, FOREGROUND, fill)

    def _render_countdown(self) -> None:
        number = self.question_font.render(str(self._countdown_remaining()), True, FOREGROUND)
        self.screen.blit(number, number.get_rect(center=(APP_WIDTH // 2, APP_HEIGHT // 2)))

    def _render_flowing_notes(self) -> None:
        if self.session is None:
            return
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(pygame.Rect(0, 92, APP_WIDTH, APP_HEIGHT - 92))
        song_time = self._song_position_seconds()
        has_visible_note = False
        for note in self.session.pending:
            seconds_until_note = note.timestamp - song_time
            if not -0.25 <= seconds_until_note <= NOTE_TRAVEL_SECONDS:
                continue
            lane = ("left", "down", "up", "right").index(note.direction)
            y = 132 + seconds_until_note * (APP_HEIGHT + 16 - 132) / NOTE_TRAVEL_SECONDS
            arrow = self.flow_arrows[note.direction]
            if 92 <= y <= APP_HEIGHT + 16:
                self.screen.blit(arrow, arrow.get_rect(center=(APP_WIDTH // 2 - 142 + lane * 84, round(y))))
                has_visible_note = True
        if not has_visible_note:
            self._render_next_note_marker(song_time)
        self.screen.set_clip(previous_clip)

    def _render_next_note_marker(self, song_time: float) -> None:
        if self.session is None:
            return
        next_note = next((note for note in self.session.pending if note.timestamp > song_time), None)
        if next_note is None:
            return
        lane = ("left", "down", "up", "right").index(next_note.direction)
        center_x = APP_WIDTH // 2 - 142 + lane * 84
        for offset, color in zip((-5, 0, 5), ((255, 75, 125), (255, 225, 70), (55, 225, 255))):
            pygame.draw.circle(self.screen, color, (center_x + offset, APP_HEIGHT - 14), 3)

    def _render_feedback(self) -> None:
        if self.feedback is None or self._song_position_seconds() > self.feedback_until:
            return
        icon = self.feedback_icons[self.feedback]
        self.screen.blit(icon, icon.get_rect(midtop=(720, 104)))

    def _render_result(self) -> None:
        self._render_gameplay_header()
        star_y = 222
        star_spacing = 40
        star_start_x = 253
        for index in range(5):
            self.screen.blit(self.draft_star, (star_start_x + index * star_spacing, star_y))
        earned_count = min(self.result_stars, (pygame.time.get_ticks() - self.result_started_at) // STAR_DELAY_MS)
        for index in range(earned_count):
            self.screen.blit(self.earned_star, (star_start_x + index * star_spacing, star_y))
        if earned_count >= self.result_stars and self.result_stars:
            reaction = Judgement.MISS if self.result_stars <= 2 else Judgement.OK if self.result_stars <= 4 else Judgement.GREAT
            icon = self.feedback_icons[reaction]
            self.screen.blit(icon, icon.get_rect(midleft=(star_start_x + 5 * star_spacing + 24, star_y + 16)))

    def _render_modal(self, message: str) -> None:
        dimmer = pygame.Surface((APP_WIDTH, APP_HEIGHT), pygame.SRCALPHA)
        dimmer.fill((0, 0, 0, 170))
        self.screen.blit(dimmer, (0, 0))
        frame = pygame.Rect(220, 162, 414, 156)
        pygame.draw.rect(self.screen, (20, 20, 26), frame)
        pygame.draw.rect(self.screen, (230, 230, 230), frame, width=3)
        text = self.question_font.render(message, True, FOREGROUND)
        self.screen.blit(text, text.get_rect(center=frame.center))

    def _render_song_exit_confirmation(self) -> None:
        self._render_modal(SETTINGS.song_exit_confirmation_text)
        self._render_confirmation_buttons(SETTINGS.song_exit_confirm_button, SETTINGS.song_exit_cancel_button, self.song_exit_confirmation_selected, 270)

    def _render_confirmation_buttons(self, confirm: str, cancel: str, confirm_selected: bool, y: int) -> None:
        rendered = [(self.list_font.render(label, True, (255, 150, 100) if selected else FOREGROUND), selected) for label, selected in ((confirm, confirm_selected), (cancel, not confirm_selected))]
        gap = 72
        x = (APP_WIDTH - sum(text.get_width() for text, _ in rendered) - gap) // 2
        for text, selected in rendered:
            self.screen.blit(text, (x, y))
            if selected:
                self._blit_chevron(x - 34, y, (255, 150, 100))
            x += text.get_width() + gap

    def _blit_chevron(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        self.screen.blit(self.list_font.render(">", True, color), (x, y))

    def _song_position_seconds(self) -> float:
        return self._audio_position_seconds() + SETTINGS.timing_offset_ms / 1000

    def _audio_position_seconds(self) -> float:
        return 0.0 if self.current_screen is Screen.COUNTDOWN else max(0, pygame.mixer.music.get_pos()) / 1000

    def _show_judgement(self, result: JudgedNote | None) -> None:
        if result is not None:
            self._show_feedback(result.judgement)

    def _show_feedback(self, judgement: Judgement) -> None:
        self.feedback = judgement
        self.feedback_until = self._song_position_seconds() + FEEDBACK_DURATION_SECONDS

    def _countdown_remaining(self) -> int:
        return max(0, COUNTDOWN_SECONDS - int((pygame.time.get_ticks() - self.countdown_started_at) / 1000))

    def _load_receptors(self) -> dict[str, pygame.Surface]:
        arrow = pygame.image.load(FONT_PATH.parent.parent / "gameplay" / "arrow.png").convert_alpha()
        return {"up": arrow, "down": pygame.transform.rotate(arrow, 180), "left": pygame.transform.rotate(arrow, 90), "right": pygame.transform.rotate(arrow, -90)}

    def _load_flow_arrows(self) -> dict[str, pygame.Surface]:
        arrow = pygame.image.load(FONT_PATH.parent.parent / "gameplay" / "arrow-flow.png").convert_alpha()
        return {"up": arrow, "down": pygame.transform.rotate(arrow, 180), "left": pygame.transform.rotate(arrow, 90), "right": pygame.transform.rotate(arrow, -90)}

    def _load_feedback_icons(self) -> dict[Judgement, pygame.Surface]:
        asset_directory = FONT_PATH.parent.parent / "gameplay"
        return {
            Judgement.GREAT: pygame.image.load(asset_directory / "heart.png").convert_alpha(),
            Judgement.OK: pygame.image.load(asset_directory / "thumb.png").convert_alpha(),
            Judgement.MISS: pygame.image.load(asset_directory / "shrug.png").convert_alpha(),
        }

    def _load_result_stars(self) -> tuple[pygame.Surface, pygame.Surface]:
        star = pygame.image.load(FONT_PATH.parent.parent / "gameplay" / "star.png").convert_alpha()
        draft = star.copy()
        draft.fill((110, 110, 110), special_flags=pygame.BLEND_RGBA_MULT)
        earned = star.copy()
        earned.fill((255, 220, 45), special_flags=pygame.BLEND_RGBA_MULT)
        return draft, earned

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
        for stripe, x in enumerate(range(-mask.get_height(), mask.get_width() + mask.get_height(), 12)):
            color = colorsys.hsv_to_rgb((stripe % 12) / 12, 0.85, 1.0)
            pygame.draw.polygon(rainbow, tuple(round(channel * 255) for channel in color), ((x, 0), (x + 12, 0), (x + 12 + mask.get_height(), mask.get_height()), (x + mask.get_height(), mask.get_height())))
        rainbow.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return rainbow
