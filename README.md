# pi-dance

A deliberately small Dance Dance Revolution-style rhythm game for very low-end hardware, primarily the Raspberry Pi 1 B+ (256 MB), built with Python and Pygame.

The first goal is not to build a complete StepMania clone. The MVP exists to answer a simpler question: **will the kids actually want to use the dance pad?**

## MVP

The application flow is intentionally small:

```text
BOOT -> SPLASH -> SONG SELECT -> PLAYING <-> PAUSED -> RESULT -> SONG SELECT
```

- Select a song with Up/Down.
- Start with the dance-pad Start button or Enter/Space on a keyboard.
- Follow scrolling directional notes.
- Correct steps score points.
- Start pauses/resumes during a song.
- Select / Escape returns to the song list.
- Every completed song ends with a small celebratory result screen, regardless of score.
- Results are expressed as a simple star rating. No persistent high scores in the MVP.

## Display model

The application canvas is **854x480**.

HUD, menus, text and result screens render natively at 854x480 so they can use the full output resolution and remain readable.

Gameplay graphics use a lower-resolution pixel-art coordinate system and are scaled by an integer factor with nearest-neighbour scaling. The exact gameplay viewport size is intentionally not fixed yet; it should follow from the HUD layout rather than constrain it.

For displays that reject 854x480 and run at 1280x720, the 854x480 application canvas should be shown 1:1 and centered with black borders. The application does not require a responsive 720p layout.

## Target hardware and development environment

The deployment/performance target is:

- Raspberry Pi 1 B+
- 256 MB RAM
- DietPi / Raspberry Pi OS-class Linux environment
- USB dance pad
- HDMI display
- 30 FPS minimum target

The Raspberry Pi is **not** the primary development surface. The game must run normally on desktop macOS and Linux so almost all development, testing and iteration can happen there.

Keyboard input is a **first-class controller**, not a debug fallback. Everything required to play and navigate the MVP must be possible from the keyboard.

The [`matejbudzel/pi-286-games`](https://github.com/matejbudzel/pi-286-games) repository is the authoritative reference for the target Raspberry Pi 1 B+ / DietPi device, display environment, deployment conventions and known hardware constraints. This project should reuse that operational knowledge where applicable, but should not inherit DOSBox-specific architectural constraints.

## Audio and songs

Runtime audio is uncompressed WAV so the Pi does not need to decode MP3 during gameplay.

No copyrighted music or community chart files belong in this repository. The game loads song bundles from a configurable external directory.

A song bundle is expected to look roughly like this:

```text
love-story/
  song.wav
  chart.sm
  song.json
```

Example metadata:

```json
{
  "title": "Love Story",
  "artist": "Taylor Swift",
  "audio": "song.wav",
  "chart": "chart.sm",
  "chart_difficulty": "Beginner"
}
```

The exact schema may evolve while the first real community charts are integrated.

## Chart philosophy

The MVP should support only the useful subset of StepMania charts rather than attempting complete StepMania compatibility.

The chart loader should translate source files into a small internal representation based on absolute note timestamps. Gameplay, rendering and scoring should not depend directly on the StepMania format.

Initial scope:

- four-panel single-player dance
- tap notes
- BPM and song offset
- Beginner/Easy community charts

More advanced features such as mines, rolls, complex gimmicks and full `.sm`/`.ssc` compatibility are non-goals until real songs require them.

## Timing and scoring

Audio playback is the timing authority. Note timing must not depend on rendered frame count.

The MVP needs only a small scoring model such as hits, misses and total notes, converted to a friendly 1-5 star result. There is no fail state: finishing the song is always celebrated.

Global audio/input timing offsets should be configurable so HDMI/display/input latency can be tuned on the real Raspberry Pi setup.

## Non-goals for the first MVP

- persistent high scores
- user profiles
- difficulty selection UI
- multiplayer
- combo multipliers
- life/fail mechanics
- online services
- cover art or background video
- lyrics
- MP3 playback
- chart editor
- automatic chart generation
- exhaustive StepMania compatibility
- touchscreen/mouse-first UI
- settings UI

## Development

Requires Python 3.11+ for desktop development.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pi-dance
```

The initial scaffold currently provides the portable application shell. Song discovery, chart parsing, audio playback and scoring will be added incrementally.