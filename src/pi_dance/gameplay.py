"""Timing-based gameplay state, independent from Pygame rendering and devices."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .charts import Note


GREAT_WINDOW_SECONDS = 0.13
OK_WINDOW_SECONDS = 0.28
DOUBLE_TAP_SECONDS = 0.12
CLOSE_NOTE_GAP_SECONDS = 0.16


class Judgement(Enum):
    GREAT = auto()
    OK = auto()
    MISS = auto()


@dataclass(frozen=True)
class JudgedNote:
    note: Note
    judgement: Judgement


class Session:
    """Tracks pending chart notes and judges them against an audio song clock."""

    def __init__(self, notes: tuple[Note, ...]) -> None:
        self.pending = list(notes)
        self.judgements: list[JudgedNote] = []
        self.last_press_was_ignored = False
        self._last_successful_press: tuple[float, Note] | None = None

    def press(self, direction: str, song_time: float) -> JudgedNote | None:
        self.last_press_was_ignored = self._is_accidental_double_tap(song_time)
        if self.last_press_was_ignored:
            return None
        candidates = [
            note
            for note in self.pending
            if note.direction == direction and abs(note.timestamp - song_time) <= OK_WINDOW_SECONDS
        ]
        if not candidates:
            return None
        note = min(candidates, key=lambda candidate: abs(candidate.timestamp - song_time))
        self.pending.remove(note)
        judgement = Judgement.GREAT if abs(note.timestamp - song_time) <= GREAT_WINDOW_SECONDS else Judgement.OK
        result = JudgedNote(note=note, judgement=judgement)
        self.judgements.append(result)
        self._last_successful_press = (song_time, note)
        return result

    def _is_accidental_double_tap(self, song_time: float) -> bool:
        if self._last_successful_press is None:
            return False
        previous_time, previous_note = self._last_successful_press
        if not 0 < song_time - previous_time <= DOUBLE_TAP_SECONDS:
            return False
        next_note = self.pending[0] if self.pending else None
        return next_note is None or next_note.timestamp - previous_note.timestamp > CLOSE_NOTE_GAP_SECONDS

    def expire(self, song_time: float) -> list[JudgedNote]:
        expired: list[JudgedNote] = []
        while self.pending and self.pending[0].timestamp < song_time - OK_WINDOW_SECONDS:
            note = self.pending.pop(0)
            result = JudgedNote(note=note, judgement=Judgement.MISS)
            self.judgements.append(result)
            expired.append(result)
        return expired

    def stars(self) -> int:
        if not self.judgements:
            return 1
        score = sum(2 if result.judgement is Judgement.GREAT else 1 if result.judgement is Judgement.OK else 0 for result in self.judgements)
        return 1 + round(4 * score / (2 * len(self.judgements)))
