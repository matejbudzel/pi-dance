from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path


APP_WIDTH = 854
APP_HEIGHT = 480
TARGET_FPS = 30
WINDOW_TITLE = "pi-dance"


@dataclass(frozen=True)
class Settings:
    title: str
    song_directory: Path
    exit_item_title: str
    exit_confirmation_text: str
    exit_confirm_button: str
    exit_cancel_button: str


def load_settings(config_path: Path = Path("pi-dance.ini")) -> Settings:
    """Load user-editable settings, falling back to portable defaults."""
    parser = ConfigParser()
    parser.read(config_path, encoding="utf-8")

    title = parser.get("game", "title", fallback="Tancuj, tancuj, vykrúcaj!").strip()
    song_directory_value = parser.get("songs", "directory", fallback="songs").strip()
    song_directory = Path(song_directory_value).expanduser()
    if not song_directory.is_absolute():
        song_directory = config_path.parent / song_directory
    return Settings(
        title=title or "Tancuj, tancuj, vykrúcaj!",
        song_directory=song_directory,
        exit_item_title=parser.get("exit", "item_title", fallback="Koniec").strip() or "Koniec",
        exit_confirmation_text=parser.get("exit", "confirmation_text", fallback="Naozaj skončiť?").strip() or "Naozaj skončiť?",
        exit_confirm_button=parser.get("exit", "confirm_button", fallback="Áno").strip() or "Áno",
        exit_cancel_button=parser.get("exit", "cancel_button", fallback="Nie").strip() or "Nie",
    )


SETTINGS = load_settings()
SONG_DIRECTORY = SETTINGS.song_directory

TITLE = SETTINGS.title
FONT_PATH = Path(__file__).parent / "assets" / "fonts" / "sweet16mono.ttf"

BACKGROUND = (0, 0, 0)
FOREGROUND = (240, 240, 240)
