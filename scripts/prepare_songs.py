#!/usr/bin/env python3
"""Create Pi-Dance runtime files from downloaded StepMania song bundles.

The input directory is deliberately external to the repository: it may contain
copyrighted audio and community charts.  This tool preserves downloaded source
files and creates only ``song.wav`` and ``song.json`` alongside them.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


AUDIO_EXTENSIONS = (".ogg", ".mp3")
DIFFICULTY_ORDER = {
    "beginner": 0,
    "easy": 1,
    "medium": 2,
    "hard": 3,
    "challenge": 4,
    "edit": 5,
}


@dataclass(frozen=True)
class ChartChoice:
    difficulty: str
    meter: int


def sm_tag(contents: str, name: str) -> str | None:
    """Return a simple StepMania tag value, if present."""
    match = re.search(rf"#{re.escape(name)}\s*:(.*?);", contents, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def easiest_dance_single(contents: str) -> ChartChoice:
    """Choose the least difficult dance-single chart declared by an .sm file."""
    charts: list[ChartChoice] = []
    for match in re.finditer(r"#NOTES\s*:(.*?);", contents, re.IGNORECASE | re.DOTALL):
        fields = match.group(1).split(":", 5)
        if len(fields) != 6 or fields[0].strip().lower() != "dance-single":
            continue
        difficulty = fields[2].strip()
        try:
            meter = int(fields[3].strip())
        except ValueError:
            continue
        charts.append(ChartChoice(difficulty=difficulty, meter=meter))

    if not charts:
        raise ValueError("no usable dance-single chart")

    return min(
        charts,
        key=lambda chart: (DIFFICULTY_ORDER.get(chart.difficulty.lower(), 99), chart.meter),
    )


def source_url(song_dir: Path) -> str | None:
    """Read the original download URL from the bundle's existing text file."""
    for path in sorted(song_dir.glob("*.txt")):
        value = path.read_text(encoding="utf-8").strip()
        if value.startswith(("https://", "http://")):
            return value
    return None


def input_audio(song_dir: Path) -> Path:
    audio = [path for path in song_dir.iterdir() if path.suffix.lower() in AUDIO_EXTENSIONS]
    if len(audio) != 1:
        raise ValueError(f"expected exactly one MP3 or OGG file, found {len(audio)}")
    return audio[0]


def audio_duration_seconds(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return round(float(result.stdout.strip()), 3)


def prepare_song(song_dir: Path, overwrite: bool, dry_run: bool) -> None:
    sm_files = sorted(song_dir.glob("*.sm"))
    if len(sm_files) != 1:
        raise ValueError(f"expected exactly one .sm file, found {len(sm_files)}")

    sm_path = sm_files[0]
    sm_contents = sm_path.read_text(encoding="utf-8-sig")
    choice = easiest_dance_single(sm_contents)
    source_audio = input_audio(song_dir)
    wav_path = song_dir / "song.wav"
    metadata_path = song_dir / "song.json"

    if not overwrite and (wav_path.exists() or metadata_path.exists()):
        raise FileExistsError("song.wav or song.json already exists (pass --overwrite to replace it)")

    title = sm_tag(sm_contents, "TITLE") or song_dir.name
    artist = sm_tag(sm_contents, "ARTIST") or ""
    metadata = {
        "title": title,
        "artist": artist,
        "duration_seconds": audio_duration_seconds(source_audio),
        "audio": wav_path.name,
        "chart": sm_path.name,
        "chart_style": "dance-single",
        "chart_difficulty": choice.difficulty,
        "chart_meter": choice.meter,
        "source_url": source_url(song_dir),
    }

    print(f"{song_dir.name}: {source_audio.name} -> {wav_path.name}; {choice.difficulty} {choice.meter}")
    if dry_run:
        return

    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(source_audio), "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", str(wav_path)],
        check=True,
    )
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song_directory", type=Path, help="directory containing one directory per downloaded song")
    parser.add_argument("--overwrite", action="store_true", help="replace existing generated song.wav and song.json files")
    parser.add_argument("--dry-run", action="store_true", help="validate and list changes without writing files")
    args = parser.parse_args()

    failures = 0
    for song_dir in sorted(path for path in args.song_directory.iterdir() if path.is_dir()):
        try:
            prepare_song(song_dir, args.overwrite, args.dry_run)
        except (OSError, subprocess.CalledProcessError, ValueError) as error:
            failures += 1
            print(f"{song_dir.name}: skipped: {error}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
