# audio_metrics

A command-line tool to compare audio/media files side-by-side, showing file metadata and audio statistics (RMS, peak, crest factor, A-weighted levels).

I wrote this because I wanted a quick way to check the sample rate, bit depth, and other properties of audio files, and to optionally compare them side-by-side. It can be useful for checking the output of audio processing scripts, or comparing different versions of a file.

## Running

Run directly from GitHub with uvx:

```bash
uvx --from git+https://github.com/martin-hunt/audio_metrics media_compare <input1> [input2] [input3] [--verbose]
```

Analyse a single file:

```bash
uv run python audio_metrics.py <input>
```

Compare two or three files:

```bash
uv run python audio_metrics.py <input1> <input2> [<input3>]
```

Show metadata tags (ID3, Vorbis comment, etc.):

```bash
uv run python audio_metrics.py <input1> <input2> --verbose
```

After `uv sync` the script is also available as an installed entry point:

```bash
uv run media_compare <input1> <input2>
```

## Running the tests

```bash
uv run pytest test/
```

## Example output

### Single file

```bash
$ uv run python audio_metrics.py test/files/LDC93S1.wav

            test/files/LDC93S1.wav
┌─────────────────────────┬──────────────────┐
│ File Size               │          0.09 MB │
│ Sample Rate             │         16.0 kHz │
│ Channels                │                1 │
│ Duration                │     2.92 seconds │
│ Total Samples           │            46797 │
│ Bitrate                 │      256.10 kbps │
│ Format                  │              WAV │
│ Codec                   │           PCM_16 │
│ Format Settings         │  Little / Signed │
│ Bit Rate Mode           │              CBR │
│ Bit Depth               │               16 │
│                         │                  │
│ Audio Statistics        │                  │
│ Peak                    │      -21.40 dBFS │
│ RMS                     │        -41.43 dB │
│ Crest Factor            │ 10.04 (20.04 dB) │
│ A-weighted RMS          │        -43.39 dB │
│ A-weighted Crest Factor │ 14.35 (23.14 dB) │
└─────────────────────────┴──────────────────┘
```

### Comparison (two files)

Differences between files are highlighted in yellow in the terminal.

```bash
$ uv run python audio_metrics.py test/files/LDC93S1.wav test/files/Free_Test_Data_100KB_OGG.ogg

                            Audio Metrics Comparison
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                         ┃ test/files/LDC93S1.wav ┃ test/files/Free_Test_D... ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ File Size               │                0.09 MB │                   0.10 MB │
│ Sample Rate             │               16.0 kHz │                  44.1 kHz │
│ Channels                │                      1 │                         2 │
│ Duration                │           2.92 seconds │              4.95 seconds │
│ Total Samples           │                  46797 │                    218241 │
│ Bitrate                 │            256.10 kbps │               166.95 kbps │
│ Format                  │                    WAV │                       OGG │
│ Codec                   │                 PCM_16 │                    VORBIS │
│ Format Settings         │        Little / Signed │                       N/A │
│ Bit Rate Mode           │                    CBR │                       VBR │
│ Bit Depth               │                     16 │                       N/A │
│ Writing Library         │                    N/A │   Xiph.Org libVorbis I... │
│                         │                        │                           │
│ Audio Statistics        │                        │                           │
│ Peak                    │                 -21.40 │                      0.09 │
│ RMS                     │                 -41.43 │                    -14.16 │
│ Crest Factor            │       10.04 (20.04 dB) │           5.16 (14.25 dB) │
│ A-weighted RMS          │                 -43.39 │                    -19.48 │
│ A-weighted Crest Factor │       14.35 (23.14 dB) │           7.27 (17.23 dB) │
└─────────────────────────┴────────────────────────┴───────────────────────────┘
```

## Supported formats

| Format | Read | Tags |
|--------|------|------|
| WAV    | ✓    | ✓ (if ID3 embedded) |
| FLAC   | ✓    | ✓ (Vorbis comment) |
| OGG Vorbis | ✓ | ✓ (Vorbis comment) |
| OGG Opus   | ✓ | ✓ (Vorbis comment) |
| MP3    | ✓    | ✓ (ID3) |
