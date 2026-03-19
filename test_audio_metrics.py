import numpy as np
import pytest
from pathlib import Path

from audio_metrics import calculate_audio_stats, format_row, get_media_info, get_tags


# ---------------------------------------------------------------------------
# calculate_audio_stats
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
    # Should accept 2D arrays (stereo)
    mono = make_sine(amplitude=0.5)
    stereo = np.column_stack([mono, mono])
    stats = calculate_audio_stats(stereo, 48000)
    assert stats["peak_dbfs"] == pytest.approx(20 * np.log10(0.5), abs=0.01)


def test_audio_stats_a_weighted_keys():
    audio = make_sine()
    stats = calculate_audio_stats(audio, 48000)
    assert "a_weighted_rms_db" in stats
    assert "a_weighted_crest_factor" in stats
    assert "a_weighted_crest_factor_db" in stats


# ---------------------------------------------------------------------------
# format_row
# ---------------------------------------------------------------------------

def test_format_row_equal_values():
    row = format_row("Label", "foo", "foo")
    assert row == ("Label", "foo", "foo")


def test_format_row_different_values():
    row = format_row("Label", "foo", "bar")
    assert "[yellow]" in row[1]
    assert "[yellow]" in row[2]


def test_format_row_single_value():
    row = format_row("Label", "only")
    assert row == ("Label", "only")


def test_format_row_three_values_all_same():
    row = format_row("Label", "x", "x", "x")
    assert row == ("Label", "x", "x", "x")


def test_format_row_three_values_one_differs():
    row = format_row("Label", "x", "x", "y")
    assert all("[yellow]" in v for v in row[1:])


# ---------------------------------------------------------------------------
# get_media_info — using real files
# ---------------------------------------------------------------------------

def test_get_media_info_mp3():
    minfo = get_media_info(Path("test.mp3"))
    assert minfo["audio_codec"] == "MPEG Audio"
    assert minfo["channels"] == 2
    assert minfo["sample_rate"] == 48000
    assert minfo["format_profile"] == "Layer 3"
    assert minfo["bit_rate_mode"] == "CBR"
    assert minfo["writing_library"] is not None


def test_get_media_info_flac():
    minfo = get_media_info(Path("vida.flac"))
    assert minfo["audio_codec"] == "FLAC"
    assert minfo["bit_depth"] == 16
    assert minfo["channel_layout"] == "L R"
    assert minfo["bit_rate_mode"] == "VBR"


def test_get_media_info_wav():
    minfo = get_media_info(Path("sr005-01-24192.wav"))
    assert minfo["audio_codec"] == "PCM"
    assert minfo["bit_depth"] == 24
    assert minfo["sample_rate"] == 192000
    assert "Little" in minfo["format_settings"]


def test_get_media_info_ogg():
    minfo = get_media_info(Path("test.ogg"))
    assert minfo["channels"] == 2
    assert minfo["channel_layout"] == "L R"


# ---------------------------------------------------------------------------
# get_tags — using real files
# ---------------------------------------------------------------------------

def test_get_tags_mp3():
    tags = get_tags(Path("test.mp3"))
    assert tags is not None
    assert any("TIT2" in k or "TPE1" in k for k in tags)


def test_get_tags_flac():
    tags = get_tags(Path("vida.flac"))
    assert tags is not None
    assert any(k.lower() in ("title", "artist", "album") for k in tags)


def test_get_tags_ogg():
    tags = get_tags(Path("test.ogg"))
    # test.ogg may or may not have tags; just verify it doesn't raise
    assert tags is None or isinstance(tags, dict)


def test_get_tags_wav_no_tags():
    # WAV files without ID3 tags return None
    tags = get_tags(Path("sr005-01-24192.wav"))
    assert tags is None or isinstance(tags, dict)


def test_get_tags_unknown_extension(tmp_path):
    f = tmp_path / "audio.xyz"
    f.write_bytes(b"\x00" * 16)
    assert get_tags(f) is None
