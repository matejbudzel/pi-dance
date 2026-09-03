from __future__ import annotations

from enum import Enum, auto

import pygame


class Action(Enum):
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    START = auto()
    SELECT = auto()


KEY_ACTIONS = {
    pygame.K_LEFT: Action.LEFT,
    pygame.K_RIGHT: Action.RIGHT,
    pygame.K_UP: Action.UP,
    pygame.K_DOWN: Action.DOWN,
    pygame.K_RETURN: Action.START,
    pygame.K_SPACE: Action.START,
    pygame.K_ESCAPE: Action.SELECT,
}


def actions_from_event(event: pygame.event.Event) -> list[Action]:
    if event.type != pygame.KEYDOWN:
        return []

    action = KEY_ACTIONS.get(event.key)
    return [action] if action is not None else []
