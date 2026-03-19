#!/usr/bin/env python3
import sys
from pathlib import Path
from typing import Annotated

import cyclopts
import numpy as np
import soundfile as sf
from ABC_weighting import A_weight
from mutagen.flac import FLAC
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE
from pymediainfo import MediaInfo
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = cyclopts.App(name="audio_metrics", help="Audio Media Metrics Tool")
console = Console()


def calculate_audio_stats(audio_data: np.ndarray, sample_rate: int) -> dict:
    audio_float = audio_data.astype(np.float64)

    rms_linear = np.sqrt(np.mean(audio_float ** 2))
    rms_db = 20 * np.log10(rms_linear + 1e-12)

    peak_linear = np.max(np.abs(audio_float))
    peak_dbfs = 20 * np.log10(peak_linear + 1e-12)

    crest_factor = peak_linear / (rms_linear + 1e-12)
    crest_factor_db = 20 * np.log10(crest_factor)

    filtered_audio = A_weight(audio_float, sample_rate)
    a_peak_linear = np.max(np.abs(filtered_audio))
    a_weighted_rms_linear = np.sqrt(np.mean(filtered_audio ** 2))
    a_weighted_rms_db = 20 * np.log10(a_weighted_rms_linear + 1e-12)
    a_weighted_crest_factor = a_peak_linear / (a_weighted_rms_linear + 1e-12)
    a_weighted_crest_factor_db = 20 * np.log10(a_weighted_crest_factor)

    return {
        "rms_db": rms_db,
        "peak_dbfs": peak_dbfs,
        "crest_factor": crest_factor,
        "crest_factor_db": crest_factor_db,
        "a_weighted_rms_db": a_weighted_rms_db,
        "a_weighted_crest_factor": a_weighted_crest_factor,
        "a_weighted_crest_factor_db": a_weighted_crest_factor_db,
    }


def get_media_info(file_path) -> dict:
    media_info = MediaInfo.parse(file_path)
    minfo = {}
    for track in media_info.tracks:
        if track.track_type == "General":
            minfo.update({
                "file_size": track.file_size,
                "duration": track.duration / 1000,
                "bitrate": track.overall_bit_rate / 1000,
            })
        elif track.track_type == "Audio":
            minfo.update({
                "audio_codec": track.format,
                "sample_rate": track.sampling_rate,
                "channels": track.channel_s,
                "format_version": track.format_version,
                "format_profile": track.format_profile,
                "format_settings": track.format_settings,
                "bit_rate_mode": track.bit_rate_mode,
                "writing_application": track.writing_application,
                "writing_library": track.writing_library,
                "bit_depth": track.bit_depth,
                "channel_layout": track.channel_layout,
            })
        elif track.track_type == "Video":
            minfo.update({
                "video_codec": track.format,
                "resolution": f"{track.width}x{track.height}",
            })
    return minfo


def get_tags(path: Path) -> dict[str, str] | None:
    """Extract metadata tags based on file type. Returns ordered dict of label->value, or None."""
    suffix = path.suffix.lower()

    if suffix == ".mp3":
        try:
            tags = ID3(str(path))
        except ID3NoHeaderError:
            return None
        if not tags:
            return None
        result = {}
        for key, frame in sorted(tags.items()):
            result[key] = str(frame)
        return result

    if suffix in (".ogg", ".oga"):
        try:
            tags = OggVorbis(str(path))
        except Exception:
            return None
        if not tags:
            return None
        result = {}
        for key, values in sorted(tags.items()):
            result[key] = ", ".join(values)
        return result

    if suffix == ".flac":
        try:
            tags = FLAC(str(path))
        except Exception:
            return None
        if not tags:
            return None
        result = {}
        for key, values in sorted(tags.items()):
            result[key] = ", ".join(values)
        return result

    if suffix == ".wav":
        try:
            tags = WAVE(str(path))
        except Exception:
            return None
        if not tags or not tags.tags:
            return None
        result = {}
        for key, frame in sorted(tags.tags.items()):
            result[key] = str(frame)
        return result

    return None


def print_tags(path: Path, tags: dict[str, str]) -> None:
    table = Table(title=f"Metadata — {path.name}", show_header=False)
    table.add_column("Tag", style="cyan", no_wrap=True)
    table.add_column("Value", justify="left")
    for key, value in tags.items():
        table.add_row(key, value)
    console.print(table)


def load_file(path: Path) -> tuple[dict, dict, dict]:
    """Load a file and return (sf_info, minfo, stats)."""
    audio_data, sample_rate = sf.read(str(path))
    sf_info = sf.info(str(path))
    minfo = get_media_info(path)
    num_channels = 1 if audio_data.ndim == 1 else audio_data.shape[1]
    duration = len(audio_data) / sample_rate
    total_samples = len(audio_data)
    stats = calculate_audio_stats(audio_data, sample_rate)
    return {
        "sf_info": sf_info,
        "minfo": minfo,
        "sample_rate": sample_rate,
        "num_channels": num_channels,
        "duration": duration,
        "total_samples": total_samples,
        "stats": stats,
    }


def format_row(label: str, *values: str) -> tuple:
    """Return a row tuple, highlighting all values in yellow if they differ."""
    if len(set(values)) > 1:
        return (label, *[f"[yellow]{v}[/yellow]" for v in values])
    return (label, *values)


def print_single(path: Path, data: dict) -> None:
    minfo = data["minfo"]
    sf_info = data["sf_info"]
    stats = data["stats"]

    table = Table(title=str(path), show_header=False)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", justify="right")

    table.add_row("File Size", f"{minfo['file_size'] / (1024 * 1024):.2f} MB")
    table.add_row("Sample Rate", f"{data['sample_rate'] / 1000:.1f} kHz")
    table.add_row("Channels", str(data["num_channels"]))
    table.add_row("Duration", f"{data['duration']:.2f} seconds")
    table.add_row("Total Samples", str(data["total_samples"]))
    table.add_row("Bitrate", f"{minfo['bitrate']:.2f} kbps")
    table.add_row("Format", sf_info.format)
    table.add_row("Codec", sf_info.subtype)
    if minfo.get("format_version"):
        table.add_row("Format Version", minfo["format_version"])
    if minfo.get("format_profile"):
        table.add_row("Format Profile", minfo["format_profile"])
    if minfo.get("format_settings"):
        table.add_row("Format Settings", minfo["format_settings"])
    if minfo.get("bit_rate_mode"):
        table.add_row("Bit Rate Mode", minfo["bit_rate_mode"])
    if minfo.get("bit_depth"):
        table.add_row("Bit Depth", str(minfo["bit_depth"]))
    if minfo.get("channel_layout"):
        table.add_row("Channel Layout", minfo["channel_layout"])
    if minfo.get("writing_application"):
        table.add_row("Writing Application", minfo["writing_application"])
    if minfo.get("writing_library"):
        table.add_row("Writing Library", minfo["writing_library"])
    if "video_codec" in minfo:
        table.add_row("Video Codec", minfo["video_codec"])
        table.add_row("Resolution", minfo["resolution"])

    table.add_row("", "")
    table.add_row("[bold]Audio Statistics", "")
    table.add_row("Peak", f"{stats['peak_dbfs']:.2f} dBFS")
    table.add_row("RMS", f"{stats['rms_db']:.2f} dB")
    table.add_row("Crest Factor", f"{stats['crest_factor']:.2f} ({stats['crest_factor_db']:.2f} dB)")
    table.add_row("A-weighted RMS", f"{stats['a_weighted_rms_db']:.2f} dB")
    table.add_row("A-weighted Crest Factor", f"{stats['a_weighted_crest_factor']:.2f} ({stats['a_weighted_crest_factor_db']:.2f} dB)")

    console.print()
    console.print(table)


def print_comparison(paths: list[Path], data: list[dict]) -> None:
    table = Table(title="Audio Metrics Comparison", show_header=True, header_style="bold magenta")
    table.add_column("", style="cyan", no_wrap=True)
    for path in paths:
        table.add_column(str(path), style="green", justify="right")

    def row(label, *values):
        table.add_row(*format_row(label, *values))

    def stat_row(label, key):
        """Highlight differences only when rounded to 2 decimal places."""
        values = [f"{d['stats'][key]:.2f}" for d in data]
        if len(set(values)) > 1:
            table.add_row(label, *[f"[yellow]{v}[/yellow]" for v in values])
        else:
            table.add_row(label, *values)

    def stat_row2(label, key1, key2):
        """Stat row for combined display (e.g. crest factor linear + dB)."""
        formatted = [f"{d['stats'][key1]:.2f} ({d['stats'][key2]:.2f} dB)" for d in data]
        keys1 = [f"{d['stats'][key1]:.2f}" for d in data]
        keys2 = [f"{d['stats'][key2]:.2f}" for d in data]
        differs = len(set(keys1)) > 1 or len(set(keys2)) > 1
        if differs:
            table.add_row(label, *[f"[yellow]{v}[/yellow]" for v in formatted])
        else:
            table.add_row(label, *formatted)

    row("File Size", *[f"{d['minfo']['file_size'] / (1024 * 1024):.2f} MB" for d in data])
    row("Sample Rate", *[f"{d['sample_rate'] / 1000:.1f} kHz" for d in data])
    row("Channels", *[str(d["num_channels"]) for d in data])
    row("Duration", *[f"{d['duration']:.2f} seconds" for d in data])
    row("Total Samples", *[str(d["total_samples"]) for d in data])
    row("Bitrate", *[f"{d['minfo']['bitrate']:.2f} kbps" for d in data])
    row("Format", *[d["sf_info"].format for d in data])
    row("Codec", *[d["sf_info"].subtype for d in data])
    if any(d["minfo"].get("format_version") for d in data):
        row("Format Version", *[d["minfo"].get("format_version") or "N/A" for d in data])
    if any(d["minfo"].get("format_profile") for d in data):
        row("Format Profile", *[d["minfo"].get("format_profile") or "N/A" for d in data])
    if any(d["minfo"].get("format_settings") for d in data):
        row("Format Settings", *[d["minfo"].get("format_settings") or "N/A" for d in data])
    if any(d["minfo"].get("bit_rate_mode") for d in data):
        row("Bit Rate Mode", *[d["minfo"].get("bit_rate_mode") or "N/A" for d in data])
    if any(d["minfo"].get("bit_depth") for d in data):
        row("Bit Depth", *[str(d["minfo"].get("bit_depth") or "N/A") for d in data])
    if any(d["minfo"].get("channel_layout") for d in data):
        row("Channel Layout", *[d["minfo"].get("channel_layout") or "N/A" for d in data])
    if any(d["minfo"].get("writing_application") for d in data):
        row("Writing Application", *[d["minfo"].get("writing_application") or "N/A" for d in data])
    if any(d["minfo"].get("writing_library") for d in data):
        row("Writing Library", *[d["minfo"].get("writing_library") or "N/A" for d in data])
    if any("video_codec" in d["minfo"] for d in data):
        row("Video Codec", *[d["minfo"].get("video_codec", "N/A") for d in data])
        row("Resolution", *[d["minfo"].get("resolution", "N/A") for d in data])

    empty = ("",) * (len(data) + 1)
    table.add_row(*empty)
    table.add_row("[bold]Audio Statistics", *[""] * len(data))

    stat_row("Peak", "peak_dbfs")
    stat_row("RMS", "rms_db")
    stat_row2("Crest Factor", "crest_factor", "crest_factor_db")
    stat_row("A-weighted RMS", "a_weighted_rms_db")
    stat_row2("A-weighted Crest Factor", "a_weighted_crest_factor", "a_weighted_crest_factor_db")

    console.print()
    console.print(table)


@app.default
def main(
    *inputs: Annotated[Path, cyclopts.Parameter(help="Input audio file path(s) — 1 to 3 files")],
    verbose: Annotated[bool, cyclopts.Parameter(name=["-v", "--verbose"], help="Enable verbose output")] = False,
) -> None:
    if not inputs:
        console.print("[red]Error: at least one input file is required[/red]")
        sys.exit(1)
    if len(inputs) > 3:
        console.print("[red]Error: at most 3 input files are supported[/red]")
        sys.exit(1)

    for path in inputs:
        if not path.exists():
            console.print(f"[red]Error: Input file '{path}' does not exist[/red]")
            sys.exit(1)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        data = []
        for path in inputs:
            task = progress.add_task(f"Loading {path}...", total=None)
            data.append(load_file(path))
            progress.update(task, completed=True)

    if len(inputs) == 1:
        print_single(inputs[0], data[0])
    else:
        print_comparison(list(inputs), data)

    if verbose:
        for path in inputs:
            tags = get_tags(path)
            if tags:
                console.print()
                print_tags(path, tags)


if __name__ == "__main__":
    app()
