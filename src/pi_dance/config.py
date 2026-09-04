import os
from pathlib import Path


APP_WIDTH = 854
APP_HEIGHT = 480
TARGET_FPS = 30
WINDOW_TITLE = "pi-dance"
SONG_DIRECTORY = Path(os.environ.get("PI_DANCE_SONGS_DIR", "songs")).expanduser()

TITLE = os.environ.get("PI_DANCE_TITLE", "Tancuj, tancuj, vykrúcaj!")
FONT_PATH = Path(__file__).parent / "assets" / "fonts" / "horizon1994.ttf"

BACKGROUND = (0, 0, 0)
FOREGROUND = (240, 240, 240)
