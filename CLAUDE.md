# audio_metrics

A command-line tool to inspect and compare 1–3 audio/media files, showing file metadata and audio statistics (RMS, peak, crest factor, A-weighted levels). With a single file it shows a single-file view; with 2–3 files it shows a side-by-side comparison with differences highlighted in yellow.

## Setup

```bash
uv sync
```

## Running

```bash
uv run audio_metrics <input1> [input2] [input3] [--verbose]
```

Or after `uv sync`, directly via the installed script:

```bash
media_compare <input1> [input2] [input3] [--verbose]
```

Or without any setup, using `uvx` to run directly from the project directory:

```bash
uvx --from . media_compare <input1> [input2] [input3] [--verbose]
```

Or directly from GitHub without cloning:

```bash
uvx --from git+https://github.com/martin-hunt/audio_metrics media_compare <input1> [input2] [input3] [--verbose]
```

`--verbose` / `-v` prints metadata tags (ID3, Vorbis, FLAC, WAV INFO) after the main table.

## Project structure

- `audio_metrics.py` — single-file application; entry point is the `app` cyclopts instance
- `ABC_weighting.py` — local copy of A/B/C psychoacoustic weighting filter implementations
- `pyproject.toml` — uv/hatch project config and dependencies

## Dependencies

- `cyclopts` — CLI framework
- `soundfile` — audio file I/O
- `scipy` — signal processing (used by ABC_weighting)
- `ABC_weighting` — local module; A/B/C filter implementations for psychoacoustic weighting
- `pymediainfo` — media container metadata (codec, bitrate, resolution)
- `mutagen` — tag reading (ID3/MP3, Vorbis/OGG, FLAC, WAV)
- `numpy` — numerical processing
- `rich` — terminal output formatting
