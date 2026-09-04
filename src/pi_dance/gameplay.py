"""Timing-based gameplay state, independent from Pygame rendering and devices."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .charts import Note


GREAT_WINDOW_SECONDS = 0.10
OK_WINDOW_SECONDS = 0.18


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

    def press(self, direction: str, song_time: float) -> JudgedNote | None:
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
        return result

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
