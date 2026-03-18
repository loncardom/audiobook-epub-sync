from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .audio import extract_audio_chunk, media_duration_seconds
from .models import BuildConfig, SpokenWord
from .text import WORD_RE


def _approximate_words_from_segment(
    text: str,
    start: float,
    end: float,
    base_index: int,
    chunk_index: int,
) -> list[SpokenWord]:
    raw_words = [match.group(0) for match in WORD_RE.finditer(text)]
    if not raw_words:
        return []

    duration = max(0.0, end - start)
    step = duration / len(raw_words) if raw_words else 0.0
    out: list[SpokenWord] = []
    for offset, word in enumerate(raw_words):
        word_start = start + (offset * step)
        word_end = start + ((offset + 1) * step if step > 0 else 0.0)
        out.append(
            SpokenWord(
                index=base_index + offset,
                word=word,
                start=word_start,
                end=word_end,
                chunk_index=chunk_index,
                segment_start=start,
                segment_end=end,
            )
        )
    return out


def _parse_whisper_json(
    payload: dict,
    chunk_offset: float,
    start_index: int,
    chunk_index: int,
) -> list[SpokenWord]:
    words: list[SpokenWord] = []
    next_index = start_index
    for segment in payload.get("segments", []):
        segment_words = segment.get("words") or []
        if segment_words:
            for item in segment_words:
                word = str(item.get("word", "")).strip()
                if not word:
                    continue
                words.append(
                    SpokenWord(
                        index=next_index,
                        word=word,
                        start=float(item["start"]) + chunk_offset,
                        end=float(item["end"]) + chunk_offset,
                        chunk_index=chunk_index,
                        segment_start=float(segment.get("start", 0.0)) + chunk_offset,
                        segment_end=float(segment.get("end", 0.0)) + chunk_offset,
                    )
                )
                next_index += 1
            continue

        approximated = _approximate_words_from_segment(
            text=str(segment.get("text", "")),
            start=float(segment.get("start", 0.0)) + chunk_offset,
            end=float(segment.get("end", 0.0)) + chunk_offset,
            base_index=next_index,
            chunk_index=chunk_index,
        )
        words.extend(approximated)
        next_index += len(approximated)
    return words


def _transcribe_with_whisper_cli(chunk_path: Path, model_name: str) -> dict | None:
    whisper_cli = shutil.which("whisper")
    if whisper_cli is None:
        return None

    with tempfile.TemporaryDirectory(prefix="audiobook_epub_sync_whisper_") as tmp_dir:
        output_dir = Path(tmp_dir)
        subprocess.run(
            [
                whisper_cli,
                str(chunk_path),
                "--language",
                "en",
                "--model",
                model_name,
                "--task",
                "transcribe",
                "--fp16",
                "False",
                "--word_timestamps",
                "True",
                "--output_format",
                "json",
                "--output_dir",
                str(output_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        json_path = output_dir / f"{chunk_path.stem}.json"
        if not json_path.exists():
            return None
        return json.loads(json_path.read_text(encoding="utf-8"))


def _transcribe_with_faster_whisper(chunk_path: Path, model_name: str) -> dict | None:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception:
        return None

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(chunk_path), language="en", word_timestamps=True)

    payload = {"segments": []}
    for segment in segments:
        segment_payload = {
            "start": float(segment.start),
            "end": float(segment.end),
            "text": segment.text,
            "words": [],
        }
        if segment.words:
            for item in segment.words:
                if not item.word:
                    continue
                segment_payload["words"].append(
                    {
                        "word": item.word,
                        "start": float(item.start),
                        "end": float(item.end),
                    }
                )
        payload["segments"].append(segment_payload)

    return payload


def _transcribe_with_openai_whisper(chunk_path: Path, model_name: str) -> dict | None:
    try:
        import whisper  # type: ignore
    except Exception:
        return None

    model = whisper.load_model(model_name)
    result = model.transcribe(str(chunk_path), language="en", word_timestamps=True, fp16=False)
    return result if isinstance(result, dict) else None


def _transcribe_chunk(chunk_path: Path, model_name: str) -> dict:
    for backend in (
        _transcribe_with_whisper_cli,
        _transcribe_with_faster_whisper,
        _transcribe_with_openai_whisper,
    ):
        payload = backend(chunk_path, model_name)
        if payload is not None:
            return payload

    raise RuntimeError(
        "No ASR backend available. Install `whisper`, `faster-whisper`, or `openai-whisper`."
    )


def extract_spoken_words(config: BuildConfig) -> list[SpokenWord]:
    duration = media_duration_seconds(config.audio_path)
    chunk_seconds = max(1, int(config.chunk_seconds))
    spoken_words: list[SpokenWord] = []
    next_index = 0
    offset = 0.0
    chunk_index = 0

    while offset < duration:
        current_length = min(float(chunk_seconds), duration - offset)
        chunk_path = extract_audio_chunk(config.audio_path, offset, current_length)
        try:
            payload = _transcribe_chunk(chunk_path, config.asr_model)
            chunk_words = _parse_whisper_json(payload, offset, next_index, chunk_index)
            spoken_words.extend(chunk_words)
            next_index += len(chunk_words)
        finally:
            shutil.rmtree(chunk_path.parent, ignore_errors=True)
        offset += float(chunk_seconds)
        chunk_index += 1

    return spoken_words
