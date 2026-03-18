from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class EpubWord:
    index: int
    word: str
    spine: int
    href: str
    path: str
    cfi: str
    align_tokens: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SpokenWord:
    index: int
    word: str
    start: float
    end: float
    chunk_index: int | None = None
    segment_start: float | None = None
    segment_end: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TimelineEntry:
    start: float
    end: float
    word: str
    spoken: str | None
    spine: int | None
    cfi: str
    repaired: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BuildConfig:
    epub_path: Path
    audio_path: Path
    output_path: Path
    work_dir: Path
    chunk_seconds: int = 300
    asr_model: str = "base"
    emit_report: bool = True


@dataclass(slots=True)
class BuildArtifacts:
    epub_words_path: Path
    spoken_words_path: Path | None = None
    timeline_path: Path | None = None
    report_path: Path | None = None


@dataclass(slots=True)
class BuildReport:
    status: str
    message: str
    inputs: dict[str, str]
    artifacts: dict[str, str]
    stats: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
