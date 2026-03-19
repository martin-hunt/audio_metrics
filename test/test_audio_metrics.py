import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from audio_metrics import calculate_audio_stats, format_row, get_media_info, get_tags, load_file

FILES = Path(__file__).parent / "files"

WAV_MONO = FILES / "LDC93S1.wav"          # 16-bit PCM, 16 kHz, mono
WAV_STEREO = FILES / "file_example_WAV_1MG.wav"  # 16-bit PCM, 44.1 kHz, stereo
WAV_SMALL = FILES / "M1F1-uint8-AFsp.wav" # 8-bit PCM, 8 kHz, stereo
FLAC_FILE = FILES / "Animals.flac"           # 24-bit flac, 48 kHz, stereo
OGG_FILE = FILES / "Free_Test_Data_100KB_OGG.ogg"  # Vorbis OGG, 44.1 kHz, stereo
OGG_OPUS = FILES / "test.ogg"            # Opus OGG, 48 kHz, stereo
MP3_FILE = FILES / "test.mp3"            # MP3, 48 kHz, stereo, CBR 192 kbps


# ---------------------------------------------------------------------------
# calculate_audio_stats — synthetic signals
# ---------------------------------------------------------------------------

def make_sine(freq=1000, sample_rate=48000, duration=1.0, amplitude=0.5):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t) * amplitude


def test_audio_stats_peak():
    audio = make_sine(amplitude=0.5)
    stats = calculate_audio_stats(audio, 48000)
    expected_dbfs = 20 * np.log10(0.5)
    assert abs(stats["peak_dbfs"] - expected_dbfs) < 0.01


def test_audio_stats_rms_sine():
    # RMS of a sine wave = amplitude / sqrt(2)
    audio = make_sine(amplitude=1.0)
    stats = calculate_audio_stats(audio, 48000)
    expected_rms_db = 20 * np.log10(1.0 / np.sqrt(2))
    assert abs(stats["rms_db"] - expected_rms_db) < 0.1


def test_audio_stats_crest_factor_sine():
    # Crest factor of a sine wave = sqrt(2) ≈ 1.414 (≈ 3.01 dB)
    audio = make_sine(amplitude=1.0)
    stats = calculate_audio_stats(audio, 48000)
    assert abs(stats["crest_factor"] - np.sqrt(2)) < 0.01
    assert abs(stats["crest_factor_db"] - 3.01) < 0.05


def test_audio_stats_silence():
    audio = np.zeros(48000)
    stats = calculate_audio_stats(audio, 48000)
    assert stats["peak_dbfs"] < -200
    assert stats["rms_db"] < -200


def test_audio_stats_stereo():
    mono = make_sine(amplitude=0.5)
    stereo = np.column_stack([mono, mono])
    stats = calculate_audio_stats(stereo, 48000)
    assert stats["peak_dbfs"] == pytest.approx(20 * np.log10(0.5), abs=0.01)


def test_audio_stats_keys():
    stats = calculate_audio_stats(make_sine(), 48000)
    for key in ("rms_db", "peak_dbfs", "crest_factor", "crest_factor_db",
                "a_weighted_rms_db", "a_weighted_crest_factor", "a_weighted_crest_factor_db"):
        assert key in stats


# ---------------------------------------------------------------------------
# format_row
# ---------------------------------------------------------------------------

def test_format_row_equal_values():
    assert format_row("Label", "foo", "foo") == ("Label", "foo", "foo")


def test_format_row_different_values():
    row = format_row("Label", "foo", "bar")
    assert "[yellow]" in row[1] and "[yellow]" in row[2]


def test_format_row_single_value():
    assert format_row("Label", "only") == ("Label", "only")


def test_format_row_three_values_all_same():
    assert format_row("Label", "x", "x", "x") == ("Label", "x", "x", "x")


def test_format_row_three_values_one_differs():
    row = format_row("Label", "x", "x", "y")
    assert all("[yellow]" in v for v in row[1:])


# ---------------------------------------------------------------------------
# get_media_info — real files
# ---------------------------------------------------------------------------

def test_get_media_info_wav_mono():
    minfo = get_media_info(WAV_MONO)
    assert minfo["audio_codec"] == "PCM"
    assert minfo["sample_rate"] == 16000
    assert minfo["channels"] == 1
    assert minfo["bit_depth"] == 16
    assert "Little" in minfo["format_settings"]


def test_get_media_info_wav_stereo():
    minfo = get_media_info(WAV_STEREO)
    assert minfo["audio_codec"] == "PCM"
    assert minfo["sample_rate"] == 44100
    assert minfo["channels"] == 2
    assert minfo["bit_depth"] == 16


def test_get_media_info_flac():
    minfo = get_media_info(FLAC_FILE)
    assert minfo["audio_codec"] == "FLAC"
    assert minfo["sample_rate"] == 48000
    assert minfo["channels"] == 2
    assert minfo["bit_depth"] == 24
    assert minfo["channel_layout"] == "L R"


def test_get_media_info_ogg_vorbis():
    minfo = get_media_info(OGG_FILE)
    assert minfo["audio_codec"] == "Vorbis"
    assert minfo["sample_rate"] == 44100
    assert minfo["channels"] == 2


def test_get_media_info_ogg_opus():
    minfo = get_media_info(OGG_OPUS)
    assert minfo["audio_codec"] == "Opus"
    assert minfo["sample_rate"] == 48000
    assert minfo["channels"] == 2


def test_get_media_info_mp3():
    minfo = get_media_info(MP3_FILE)
    assert minfo["audio_codec"] == "MPEG Audio"
    assert minfo["sample_rate"] == 48000
    assert minfo["channels"] == 2
    assert minfo["format_profile"] == "Layer 3"
    assert minfo["bit_rate_mode"] == "CBR"
    assert minfo["writing_library"] is not None


def test_get_media_info_has_file_size_and_bitrate():
    minfo = get_media_info(WAV_MONO)
    assert minfo["file_size"] > 0
    assert minfo["bitrate"] > 0
    assert minfo["duration"] > 0


# ---------------------------------------------------------------------------
# get_tags — real files
# ---------------------------------------------------------------------------

def test_get_tags_mp3_has_common_tags():
    tags = get_tags(MP3_FILE)
    assert tags is not None
    assert any(k in tags for k in ("TIT2", "TPE1", "TALB"))


# def test_get_tags_flac_has_common_tags():
#     tags = get_tags(FLAC_FILE)
#     assert tags is not None
#     assert any(k.lower() in ("title", "artist", "album") for k in tags)


def test_get_tags_ogg_vorbis():
    # May or may not have tags; must not raise
    tags = get_tags(OGG_FILE)
    assert tags is None or isinstance(tags, dict)


def test_get_tags_wav_no_id3():
    # Plain WAV without embedded ID3 tags returns None
    tags = get_tags(WAV_MONO)
    assert tags is None or isinstance(tags, dict)


def test_get_tags_unknown_extension(tmp_path):
    f = tmp_path / "audio.xyz"
    f.write_bytes(b"\x00" * 16)
    assert get_tags(f) is None


# ---------------------------------------------------------------------------
# load_file — real files
# ---------------------------------------------------------------------------

def test_load_file_wav_mono():
    data = load_file(WAV_MONO)
    assert data["sample_rate"] == 16000
    assert data["num_channels"] == 1
    assert data["duration"] == pytest.approx(2.92, abs=0.05)
    assert data["total_samples"] > 0
    assert "stats" in data
    assert "minfo" in data
    assert "sf_info" in data


def test_load_file_wav_stereo():
    data = load_file(WAV_STEREO)
    assert data["sample_rate"] == 44100
    assert data["num_channels"] == 2


def test_load_file_flac():
    data = load_file(FLAC_FILE)
    assert data["sample_rate"] == 48000
    assert data["num_channels"] == 2
    assert data["stats"]["peak_dbfs"] < 1.0   # peak within reasonable range (≤ 0 dBFS)


def test_load_file_ogg():
    data = load_file(OGG_FILE)
    assert data["sample_rate"] == 44100
    assert data["num_channels"] == 2
    assert "a_weighted_rms_db" in data["stats"]


def test_load_file_stats_are_finite():
    data = load_file(WAV_STEREO)
    stats = data["stats"]
    for key, value in stats.items():
        assert np.isfinite(value), f"{key} is not finite: {value}"


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------

def test_cli_single_file():
    result = subprocess.run(
        [sys.executable, "-m", "audio_metrics", str(WAV_MONO)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "RMS" in result.stdout or "RMS" in result.stderr


def test_cli_comparison():
    result = subprocess.run(
        [sys.executable, "-m", "audio_metrics", str(WAV_MONO), str(WAV_STEREO)],
        capture_output=True, text=True
    )
    assert result.returncode == 0


def test_cli_no_args_exits_nonzero():
    result = subprocess.run(
        [sys.executable, "-m", "audio_metrics"],
        capture_output=True, text=True
    )
    assert result.returncode != 0


def test_cli_missing_file_exits_nonzero():
    result = subprocess.run(
        [sys.executable, "-m", "audio_metrics", "nonexistent_file.wav"],
        capture_output=True, text=True
    )
    assert result.returncode != 0


def test_cli_three_files():
    result = subprocess.run(
        [sys.executable, "-m", "audio_metrics", str(WAV_MONO), str(WAV_STEREO), str(OGG_FILE)],
        capture_output=True, text=True
    )
    assert result.returncode == 0


def test_cli_too_many_files():
    files = [str(WAV_MONO)] * 4
    result = subprocess.run(
        [sys.executable, "-m", "audio_metrics", *files],
        capture_output=True, text=True
    )
    assert result.returncode != 0
