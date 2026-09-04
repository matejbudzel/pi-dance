"""Direct TTY and joystick input for the legacy framebuffer backend."""

from __future__ import annotations

import fcntl
import glob
import os
import select
import struct
import sys
import termios
import time
import tty

from .input import Action


KDSETMODE = 0x4B3A
KD_TEXT = 0x00
KD_GRAPHICS = 0x01
JS_EVENT = struct.Struct("IhBB")
JSIOCGNAME = 0x80806A13
JSIOCGAXES = 0x80016A11
JSIOCGBUTTONS = 0x80016A12
PAD_DEVICE_NAME = "WiseGroup.,Ltd X-PAD, Extreme Dance Pad"

PAD_ACTIONS = {
    0: Action.LEFT,
    1: Action.DOWN,
    2: Action.UP,
    3: Action.RIGHT,
    8: Action.START,
    9: Action.SELECT,
}
KEY_SEQUENCES = {
    b"\x1b[A": Action.UP,
    b"\x1bOA": Action.UP,
    b"\x1b[B": Action.DOWN,
    b"\x1bOB": Action.DOWN,
    b"\x1b[C": Action.RIGHT,
    b"\x1bOC": Action.RIGHT,
    b"\x1b[D": Action.LEFT,
    b"\x1bOD": Action.LEFT,
    b"\x1b[19~": Action.DEBUG_TOGGLE_PERFORMANCE,
    b"\r": Action.START,
    b"\n": Action.START,
    b" ": Action.START,
    b"\x1b": Action.SELECT,
    b"1": Action.DEBUG_RESULT_1,
    b"2": Action.DEBUG_RESULT_2,
    b"3": Action.DEBUG_RESULT_3,
    b"4": Action.DEBUG_RESULT_4,
    b"5": Action.DEBUG_RESULT_5,
}
MULTIBYTE_SEQUENCES = tuple(sorted((sequence for sequence in KEY_SEQUENCES if len(sequence) > 1), key=len, reverse=True))


class ConsoleInput:
    """Claim a Linux console and read keyboard plus joystick actions directly."""

    def __enter__(self) -> ConsoleInput:
        self._keyboard_fd = sys.stdin.fileno()
        if not os.isatty(self._keyboard_fd):
            raise RuntimeError("fbdev display requires an interactive Linux console")
        self._terminal_settings = termios.tcgetattr(self._keyboard_fd)
        tty.setraw(self._keyboard_fd)
        self._pending = b""
        self._pending_since = 0.0
        self._joysticks = self._open_joysticks()
        try:
            fcntl.ioctl(sys.stdout.fileno(), KDSETMODE, KD_GRAPHICS)
        except OSError:
            self._restore_terminal()
            raise RuntimeError("fbdev display requires a Linux virtual terminal")
        return self

    def __exit__(self, *_: object) -> None:
        try:
            fcntl.ioctl(sys.stdout.fileno(), KDSETMODE, KD_TEXT)
        except OSError:
            pass
        self._restore_terminal()
        for descriptor in self._joysticks:
            os.close(descriptor)
        self._joysticks = []
        sys.stdout.write("\x1bc")
        sys.stdout.flush()

    def poll_actions(self) -> list[Action]:
        actions = self._read_keyboard_actions()
        for descriptor in self._joysticks:
            try:
                data = os.read(descriptor, JS_EVENT.size * 32)
            except BlockingIOError:
                continue
            for offset in range(0, len(data) - JS_EVENT.size + 1, JS_EVENT.size):
                _, value, event_type, button = JS_EVENT.unpack_from(data, offset)
                if event_type & 0x7F == 1 and value == 1 and button in PAD_ACTIONS:
                    actions.append(PAD_ACTIONS[button])
        return actions

    def _read_keyboard_actions(self) -> list[Action]:
        if select.select([self._keyboard_fd], [], [], 0)[0]:
            if not self._pending:
                self._pending_since = time.monotonic()
            self._pending += os.read(self._keyboard_fd, 32)
        actions: list[Action] = []
        while self._pending:
            sequence = next((item for item in MULTIBYTE_SEQUENCES if self._pending.startswith(item)), None)
            if sequence is not None:
                actions.append(KEY_SEQUENCES[sequence])
                self._pending = self._pending[len(sequence):]
                continue
            if any(item.startswith(self._pending) for item in MULTIBYTE_SEQUENCES) and time.monotonic() - self._pending_since < 0.03:
                break
            action = KEY_SEQUENCES.get(self._pending[:1])
            if action is not None:
                actions.append(action)
            self._pending = self._pending[1:]
            self._pending_since = time.monotonic()
        return actions

    @staticmethod
    def _open_joysticks() -> list[int]:
        descriptors: list[int] = []
        for path in glob.glob("/dev/input/js*"):
            descriptor: int | None = None
            try:
                descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                name = fcntl.ioctl(descriptor, JSIOCGNAME, b"\0" * 128).split(b"\0", 1)[0].decode("utf-8", "replace")
                axes = fcntl.ioctl(descriptor, JSIOCGAXES, b"\0")[0]
                buttons = fcntl.ioctl(descriptor, JSIOCGBUTTONS, b"\0")[0]
                if name == PAD_DEVICE_NAME or (axes == 2 and buttons == 10):
                    descriptors.append(descriptor)
                    descriptor = None
            except OSError:
                pass
            finally:
                if descriptor is not None:
                    os.close(descriptor)
        return descriptors

    def _restore_terminal(self) -> None:
        if hasattr(self, "_terminal_settings"):
            termios.tcsetattr(self._keyboard_fd, termios.TCSADRAIN, self._terminal_settings)
