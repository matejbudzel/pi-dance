"""Pygame drawing functions with no input, audio, or state transitions."""

from __future__ import annotations

import pygame

from .assets import Assets
from .config import APP_HEIGHT, APP_WIDTH, FOREGROUND, SETTINGS
from .gameplay import Judgement, Session
from .performance import FrameTiming
from .songs import Song


LANE_DIRECTIONS = ("left", "down", "up", "right")
LANE_START_X = APP_WIDTH // 2 - 78
LANE_SPACING = 84
HEADER_HEIGHT = 92
NOTE_TRAVEL_SECONDS = 2.0
LIST_TEXT_X = 104
COVER_SIZE = 256
COVER_X = APP_WIDTH - 40 - COVER_SIZE
COVER_Y = 118
GAMEPLAY_COVER_POSITION = (16, 108)
FEEDBACK_CENTER_X = (LANE_START_X + (len(LANE_DIRECTIONS) - 1) * LANE_SPACING + 16 + APP_WIDTH) // 2
GAMEPLAY_PROGRESS_RECT = pygame.Rect(40, 16, APP_WIDTH - 80, 12)
GAMEPLAY_LANES_RECT = pygame.Rect(LANE_START_X - 28, HEADER_HEIGHT, LANE_SPACING * 3 + 56, APP_HEIGHT - HEADER_HEIGHT)
GAMEPLAY_FEEDBACK_RECT = pygame.Rect(660, 100, 170, 145)
GAMEPLAY_COUNTDOWN_RECT = pygame.Rect(APP_WIDTH // 2 - 70, APP_HEIGHT // 2 - 70, 140, 140)


def render_splash(screen: pygame.Surface, assets: Assets) -> None:
    screen.blit(assets.rainbow_title, assets.rainbow_title.get_rect(center=(APP_WIDTH // 2, APP_HEIGHT // 2)))


def render_performance_hud(screen: pygame.Surface, assets: Assets, timing: FrameTiming) -> None:
    summary = assets.performance_font.render(f"{timing.frames_per_second:4.1f} FPS  {timing.frame_ms:05.1f} ms", False, (180, 255, 180))
    detail = assets.performance_font.render(f"i{timing.input_ms:4.1f} u{timing.update_ms:4.1f} r{timing.render_ms:4.1f} p{timing.present_ms:4.1f}", False, (180, 255, 180))
    frame = pygame.Rect(0, 0, max(summary.get_width(), detail.get_width()) + 12, summary.get_height() + detail.get_height() + 12)
    frame.bottomright = (APP_WIDTH - 12, APP_HEIGHT - 10)
    pygame.draw.rect(screen, (0, 0, 0), frame)
    pygame.draw.rect(screen, (90, 150, 90), frame, width=1)
    screen.blit(summary, (frame.x + 6, frame.y + 4))
    screen.blit(detail, (frame.x + 6, frame.y + 4 + summary.get_height()))


def render_song_list(screen: pygame.Surface, assets: Assets, songs: list[Song], selected: int, first_visible_row: int, visible_rows: int) -> None:
    screen.blit(assets.rainbow_title, (40, 28))
    if not songs:
        shrug = assets.shrug_font.render(r"\_(^_^)_/", False, FOREGROUND)
        screen.blit(shrug, shrug.get_rect(center=(APP_WIDTH // 2, 240)))
        _render_exit_item(screen, assets, selected, 0, APP_HEIGHT - 70)
        return
    if selected < len(songs):
        cover = assets.cover_for(songs[selected])
        screen.blit(cover, (COVER_X, COVER_Y))
    for menu_row in range(first_visible_row, first_visible_row + visible_rows):
        y = 118 + (menu_row - first_visible_row) * 44
        if menu_row < len(songs):
            song = songs[menu_row]
            color = song.focus_color if menu_row == selected else FOREGROUND
            if menu_row == selected:
                _blit_chevron(screen, assets, 64, y, color)
            title = _ellipsize(assets.list_font, song.title, COVER_X - LIST_TEXT_X - 28)
            screen.blit(assets.list_font.render(title, False, color), (LIST_TEXT_X, y))
        elif menu_row == len(songs) + 1:
            _render_exit_item(screen, assets, selected, len(songs), y)


def render_application_exit_confirmation(screen: pygame.Surface, assets: Assets, selected: bool) -> None:
    screen.blit(assets.rainbow_title, (40, 28))
    message = assets.question_font.render(SETTINGS.exit_confirmation_text, False, FOREGROUND)
    screen.blit(message, message.get_rect(center=(APP_WIDTH // 2, 200)))
    render_confirmation_buttons(screen, assets, SETTINGS.exit_confirm_button, SETTINGS.exit_cancel_button, selected, 286)


def render_gameplay(screen: pygame.Surface, assets: Assets, song: Song | None, session: Session | None, audio_seconds: float, song_seconds: float, feedback: Judgement | None, feedback_until: float, glow_until: dict[str, int], now_ms: int) -> None:
    if song is None:
        return
    render_gameplay_base(screen, assets, song)
    _render_gameplay_dynamic(screen, assets, session, song, audio_seconds, song_seconds, feedback, feedback_until, glow_until, now_ms)


def create_gameplay_base(screen: pygame.Surface, assets: Assets, song: Song) -> pygame.Surface:
    """Build the parts of gameplay that do not change while a song is playing."""
    base = screen.copy()
    base.fill((0, 0, 0))
    render_gameplay_base(base, assets, song)
    return base


def render_gameplay_base(screen: pygame.Surface, assets: Assets, song: Song) -> None:
    _render_gameplay_header_static(screen, assets, song)
    screen.blit(assets.cover_for(song), GAMEPLAY_COVER_POSITION)
    for index, direction in enumerate(LANE_DIRECTIONS):
        center = (LANE_START_X + index * LANE_SPACING, 132)
        receptor = assets.receptors[direction]
        screen.blit(receptor, receptor.get_rect(center=center))


def render_cached_gameplay(screen: pygame.Surface, base: pygame.Surface, assets: Assets, song: Song, session: Session | None, audio_seconds: float, song_seconds: float, feedback: Judgement | None, feedback_until: float, glow_until: dict[str, int], now_ms: int, countdown: int | None) -> None:
    """Restore changing areas from a native surface, then paint only live UI."""
    for rect in (GAMEPLAY_PROGRESS_RECT, GAMEPLAY_LANES_RECT, GAMEPLAY_FEEDBACK_RECT):
        screen.blit(base, rect.topleft, rect)
    if countdown is not None:
        screen.blit(base, GAMEPLAY_COUNTDOWN_RECT.topleft, GAMEPLAY_COUNTDOWN_RECT)
    _render_gameplay_dynamic(screen, assets, session, song, audio_seconds, song_seconds, feedback, feedback_until, glow_until, now_ms)
    if countdown is not None:
        render_countdown(screen, assets, countdown)


def _render_gameplay_dynamic(screen: pygame.Surface, assets: Assets, session: Session | None, song: Song, audio_seconds: float, song_seconds: float, feedback: Judgement | None, feedback_until: float, glow_until: dict[str, int], now_ms: int) -> None:
    _render_gameplay_progress(screen, song, audio_seconds)
    _render_flowing_notes(screen, assets, session, song_seconds)
    for index, direction in enumerate(LANE_DIRECTIONS):
        center = (LANE_START_X + index * LANE_SPACING, 132)
        if now_ms <= glow_until[direction]:
            glow = assets.receptor_glows[direction]
            screen.blit(glow, glow.get_rect(center=center))
        # The static receptor is already in the cached background.  Blit it
        # again here only for normal (non-cached) rendering, after a glow.
        receptor = assets.receptors[direction]
        screen.blit(receptor, receptor.get_rect(center=center))
    if feedback is not None and song_seconds <= feedback_until:
        icon = assets.feedback_icons[feedback]
        screen.blit(icon, icon.get_rect(midtop=(FEEDBACK_CENTER_X, 104)))


def render_countdown(screen: pygame.Surface, assets: Assets, remaining: int) -> None:
    number = assets.question_font.render(str(remaining), False, FOREGROUND)
    screen.blit(number, number.get_rect(center=(APP_WIDTH // 2, APP_HEIGHT // 2)))


def render_result(screen: pygame.Surface, assets: Assets, song: Song | None, audio_seconds: float, stars: int, started_at: int, now_ms: int) -> None:
    if song is None:
        return
    _render_gameplay_header(screen, assets, song, audio_seconds)
    star_y, star_spacing, star_start_x = 222, 40, 253
    for index in range(5):
        screen.blit(assets.draft_star, (star_start_x + index * star_spacing, star_y))
    earned_count = min(stars, (now_ms - started_at) // 500)
    for index in range(earned_count):
        screen.blit(assets.earned_star, (star_start_x + index * star_spacing, star_y))
    if earned_count >= stars and stars:
        reaction = Judgement.MISS if stars <= 2 else Judgement.OK if stars <= 4 else Judgement.GREAT
        icon = assets.feedback_icons[reaction]
        screen.blit(icon, icon.get_rect(midleft=(star_start_x + 5 * star_spacing + 24, star_y + 16)))


def render_modal(screen: pygame.Surface, assets: Assets, message: str) -> None:
    dimmer = pygame.Surface((APP_WIDTH, APP_HEIGHT), pygame.SRCALPHA)
    dimmer.fill((0, 0, 0, 170))
    screen.blit(dimmer, (0, 0))
    frame = pygame.Rect(220, 162, 414, 156)
    pygame.draw.rect(screen, (20, 20, 26), frame)
    pygame.draw.rect(screen, (230, 230, 230), frame, width=3)
    text = assets.question_font.render(message, False, FOREGROUND)
    screen.blit(text, text.get_rect(center=frame.center))


def render_song_exit_confirmation(screen: pygame.Surface, assets: Assets, selected: bool) -> None:
    render_modal(screen, assets, SETTINGS.song_exit_confirmation_text)
    render_confirmation_buttons(screen, assets, SETTINGS.song_exit_confirm_button, SETTINGS.song_exit_cancel_button, selected, 270)


def render_confirmation_buttons(screen: pygame.Surface, assets: Assets, confirm: str, cancel: str, confirm_selected: bool, y: int) -> None:
    rendered = [(assets.list_font.render(label, False, (255, 150, 100) if selected else FOREGROUND), selected) for label, selected in ((confirm, confirm_selected), (cancel, not confirm_selected))]
    gap = 72
    x = (APP_WIDTH - sum(text.get_width() for text, _ in rendered) - gap) // 2
    for text, selected in rendered:
        screen.blit(text, (x, y))
        if selected:
            _blit_chevron(screen, assets, x - 34, y, (255, 150, 100))
        x += text.get_width() + gap


def _render_gameplay_header_static(screen: pygame.Surface, assets: Assets, song: Song) -> None:
    header_color = tuple(channel * 55 // 100 for channel in song.focus_color)
    pygame.draw.rect(screen, header_color, pygame.Rect(0, 0, APP_WIDTH, HEADER_HEIGHT))
    pygame.draw.rect(screen, FOREGROUND, GAMEPLAY_PROGRESS_RECT, width=2)
    screen.blit(assets.list_font.render(song.title, False, FOREGROUND), (40, 42))


def _render_gameplay_progress(screen: pygame.Surface, song: Song, audio_seconds: float) -> None:
    ratio = min(1.0, audio_seconds / song.duration_seconds)
    if ratio > 0:
        fill = GAMEPLAY_PROGRESS_RECT.copy()
        fill.width = max(1, round(GAMEPLAY_PROGRESS_RECT.width * ratio))
        pygame.draw.rect(screen, FOREGROUND, fill)


def _render_flowing_notes(screen: pygame.Surface, assets: Assets, session: Session | None, song_seconds: float) -> None:
    if session is None:
        return
    previous_clip = screen.get_clip()
    screen.set_clip(pygame.Rect(0, HEADER_HEIGHT, APP_WIDTH, APP_HEIGHT - HEADER_HEIGHT))
    has_visible_note = False
    for note in session.pending:
        seconds_until_note = note.timestamp - song_seconds
        if not -0.25 <= seconds_until_note <= NOTE_TRAVEL_SECONDS:
            continue
        lane = LANE_DIRECTIONS.index(note.direction)
        y = 132 + seconds_until_note * (APP_HEIGHT + 16 - 132) / NOTE_TRAVEL_SECONDS
        if HEADER_HEIGHT <= y <= APP_HEIGHT + 16:
            arrow = assets.flow_arrows[note.direction]
            screen.blit(arrow, arrow.get_rect(center=(LANE_START_X + lane * LANE_SPACING, round(y))))
            has_visible_note = True
    if not has_visible_note:
        _render_next_note_marker(screen, session, song_seconds)
    screen.set_clip(previous_clip)


def _render_next_note_marker(screen: pygame.Surface, session: Session, song_seconds: float) -> None:
    next_note = next((note for note in session.pending if note.timestamp > song_seconds), None)
    if next_note is None:
        return
    center_x = LANE_START_X + LANE_DIRECTIONS.index(next_note.direction) * LANE_SPACING
    for offset, color in zip((-5, 0, 5), ((255, 75, 125), (255, 225, 70), (55, 225, 255))):
        pygame.draw.circle(screen, color, (center_x + offset, APP_HEIGHT - 14), 3)


def _render_exit_item(screen: pygame.Surface, assets: Assets, selected: int, exit_index: int, y: int) -> None:
    color = (255, 150, 100) if selected == exit_index else FOREGROUND
    if selected == exit_index:
        _blit_chevron(screen, assets, 64, y, color)
    screen.blit(assets.list_font.render(SETTINGS.exit_item_title, False, color), (LIST_TEXT_X, y))


def _blit_chevron(screen: pygame.Surface, assets: Assets, x: int, y: int, color: tuple[int, int, int]) -> None:
    screen.blit(assets.list_font.render(">", False, color), (x, y))


def _ellipsize(font: pygame.font.Font, text: str, maximum_width: int) -> str:
    if font.size(text)[0] <= maximum_width:
        return text
    suffix = "..."
    shortened = text
    while shortened and font.size(shortened + suffix)[0] > maximum_width:
        shortened = shortened[:-1]
    return shortened.rstrip() + suffix
