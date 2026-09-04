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
    DEBUG_RESULT_1 = auto()
    DEBUG_RESULT_2 = auto()
    DEBUG_RESULT_3 = auto()
    DEBUG_RESULT_4 = auto()
    DEBUG_RESULT_5 = auto()
    DEBUG_TOGGLE_PERFORMANCE = auto()


KEY_ACTIONS = {
    pygame.K_LEFT: Action.LEFT,
    pygame.K_RIGHT: Action.RIGHT,
    pygame.K_UP: Action.UP,
    pygame.K_DOWN: Action.DOWN,
    pygame.K_RETURN: Action.START,
    pygame.K_SPACE: Action.START,
    pygame.K_ESCAPE: Action.SELECT,
    pygame.K_1: Action.DEBUG_RESULT_1,
    pygame.K_2: Action.DEBUG_RESULT_2,
    pygame.K_3: Action.DEBUG_RESULT_3,
    pygame.K_4: Action.DEBUG_RESULT_4,
    pygame.K_5: Action.DEBUG_RESULT_5,
    pygame.K_F8: Action.DEBUG_TOGGLE_PERFORMANCE,
}


def actions_from_event(event: pygame.event.Event) -> list[Action]:
    if event.type != pygame.KEYDOWN:
        return []

    action = KEY_ACTIONS.get(event.key)
    return [action] if action is not None else []
