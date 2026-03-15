from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def validate_audio_path(audio_path: Path) -> None:
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required but was not found on PATH.")


def media_duration_seconds(audio_path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe is required but was not found on PATH.")

    output = subprocess.check_output(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(audio_path),
        ],
        text=True,
    ).strip()
    return float(output)


def extract_audio_chunk(audio_path: Path, offset_seconds: float, length_seconds: float) -> Path:
    require_ffmpeg()
    temp_dir = Path(tempfile.mkdtemp(prefix="audiobook_epub_sync_"))
    chunk_path = temp_dir / f"chunk_{int(offset_seconds)}_{int(length_seconds)}.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(offset_seconds),
            "-i",
            str(audio_path),
            "-t",
            str(length_seconds),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(chunk_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return chunk_path
