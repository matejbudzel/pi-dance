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
- The result screen never auto-dismisses. It remains visible until the player explicitly presses Start or Select, after which the game returns to the song list.

## UI philosophy

The player-facing MVP UI should use as little text as possible.

The only required text is:

- the game title on the splash screen
- song titles in the song list

Do not add labels such as `START`, `SELECT`, `PAUSED`, `GREAT`, `MISS`, `SONG COMPLETE`, percentages, instructions or other explanatory text unless later user testing demonstrates a need.

Navigation, progress and feedback should be communicated with layout, icons, highlights and simple symbols instead of words.

### Song list

The song list is left-aligned. Each song title begins on the same vertical text axis.

The currently selected song is indicated by a chevron placed in a fixed column to the left of the titles. Moving Up/Down moves only the chevron vertically; it should not shift horizontally because of varying song-title lengths.

Conceptually:

```text
  > Love Story
    Let It Go
    Shake It Off
    Into the Unknown
```

The exact spacing and styling can evolve, but the fixed left alignment and single chevron axis are part of the MVP interaction design.

### In-game step feedback

Each judged step produces immediate visual feedback using one of three small reaction images:

- heart: best / very good hit
- thumbs-up: acceptable hit
- shrug: missed or poor hit

These are the primary in-game judgement indicators. Do not duplicate them with textual labels in the normal player UI.

The most recent reaction may remain visible briefly after judgement before disappearing or being replaced by the next one. The exact timing can be tuned during playtesting.

### Result screen

The result screen shows the final star rating and a small celebratory visual/fanfare regardless of performance. It should not display a failure state.

The result screen is modal: it remains on screen indefinitely until Start or Select is pressed. There is no timeout and no automatic return to the song list.

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

A downloaded bundle may retain its original files, but the preparation script
creates these two runtime files alongside them:

```text
love-story/
  song.wav
  song.json
  Love Story.sm
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

`song.json` is the authoritative application metadata. It includes the displayed
title, artist, duration, generated WAV filename, source `.sm` filename, selected
chart difficulty/meter, and the download URL retained from the original `.txt`
file. The exact schema may evolve while the first real community charts are integrated.

Prepare downloaded bundles on a desktop machine with ffmpeg installed:

```bash
python3 scripts/prepare_songs.py ~/pi-dance-songs --dry-run
python3 scripts/prepare_songs.py ~/pi-dance-songs
```

It chooses the easiest available `dance-single` chart entry in each `.sm` file.
The future chart loader should still expose every available chart; the MVP song
list simply uses the choice recorded in the metadata. The script will not replace
generated files unless `--overwrite` is given.

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

The internal hit-quality model should be small and map directly to the three visual reaction assets, for example `great`, `ok` and `miss` -> heart, thumbs-up and shrug.

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
- text-heavy instructions or judgement labels

## Development

Requires Python 3.11+ for desktop development.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Create the device-local configuration once; it is deliberately ignored by Git:

```bash
cp pi-dance.ini.example pi-dance.ini
```

Edit `pi-dance.ini` to localize or brand the title and point the game at the
external prepared song directory:

```ini
[game]
title = Dance, dance, spin around!

[songs]
directory = /home/matej/pi-dance-songs

[exit]
item_title = Exit
confirmation_text = Exit the game?
confirm_button = Yes
cancel_button = No

[gameplay]
pause_text = Paused
exit_confirmation_text = Stop dancing?
exit_confirm_button = Yes
exit_cancel_button = No
timing_offset_ms = 0
```

Start the game from the project directory so it reads that local configuration:

```bash
.venv/bin/pi-dance
```

The initial scaffold currently provides the portable application shell. Song discovery, chart parsing, audio playback and scoring will be added incrementally.

## Font

The included `Sweet16mono` is a pixel-perfect 8×16 bitmap-style font by Martin
Sedlák. It includes Latin Extended-A characters used by Slovak and Czech, and
is licensed under the Boost Software License 1.0; its license notice is retained
in `src/pi_dance/assets/fonts/SWEET16-LICENSE.txt`.
