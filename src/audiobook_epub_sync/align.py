from __future__ import annotations

import difflib
from typing import Any

from .models import EpubWord, SpokenWord, TimelineEntry
from .text import int_to_words, normalize_word


def align_spoken_words(
    epub_words: list[EpubWord],
    spoken_words: list[SpokenWord],
) -> list[TimelineEntry]:
    timeline, _stats = align_spoken_words_with_stats(epub_words, spoken_words)
    return timeline


def align_spoken_words_with_stats(
    epub_words: list[EpubWord],
    spoken_words: list[SpokenWord],
) -> tuple[list[TimelineEntry], dict[str, Any]]:
    epub_tokens, token_to_epub_index = _build_epub_tokens(epub_words)
    spoken_tokens, token_to_spoken_index = _build_spoken_tokens(spoken_words)
    if not epub_tokens or not spoken_tokens:
        return [], _build_empty_stats(len(epub_words), len(spoken_words))

    matcher = difflib.SequenceMatcher(a=spoken_tokens, b=epub_tokens, autojunk=False)
    token_matches: list[tuple[int, int]] = []
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            token_matches.append((block.a + offset, block.b + offset))

    timeline: list[TimelineEntry] = []
    previous_end = -1.0
    chunk_counts: dict[int, dict[str, int]] = {}

    for spoken_token_index, epub_token_index in token_matches:
        spoken_index = token_to_spoken_index[spoken_token_index]
        epub_index = token_to_epub_index[epub_token_index]
        spoken_word = spoken_words[spoken_index]
        epub_word = epub_words[epub_index]

        chunk_index = spoken_word.chunk_index if spoken_word.chunk_index is not None else 0
        chunk_counts.setdefault(chunk_index, {"spoken_words": 0, "matched_words": 0})

        if spoken_word.start < previous_end:
            continue

        timeline.append(
            TimelineEntry(
                start=spoken_word.start,
                end=spoken_word.end,
                word=epub_word.word,
                spoken=spoken_word.word,
                spine=epub_word.spine,
                cfi=epub_word.cfi,
            )
        )
        previous_end = spoken_word.end
        chunk_counts[chunk_index]["matched_words"] += 1

    for spoken_word in spoken_words:
        chunk_index = spoken_word.chunk_index if spoken_word.chunk_index is not None else 0
        chunk_counts.setdefault(chunk_index, {"spoken_words": 0, "matched_words": 0})
        chunk_counts[chunk_index]["spoken_words"] += 1

    timeline = _smooth_timeline(timeline)
    chunk_reports = []
    for chunk_index in sorted(chunk_counts):
        stats = chunk_counts[chunk_index]
        match_ratio = stats["matched_words"] / max(1, stats["spoken_words"])
        chunk_reports.append(
            {
                "chunk_index": chunk_index,
                "chunk_word_count": stats["spoken_words"],
                "matched_words": stats["matched_words"],
                "match_ratio": match_ratio,
                "accepted": match_ratio > 0.0,
            }
        )

    matched_word_count = len(timeline)
    spoken_word_count = len(spoken_words)
    stats = {
        "matched_word_count": matched_word_count,
        "spoken_word_count": spoken_word_count,
        "epub_word_count": len(epub_words),
        "match_ratio": matched_word_count / max(1, spoken_word_count),
        "accepted_chunk_count": sum(1 for report in chunk_reports if report["accepted"]),
        "chunk_count": len(chunk_reports),
        "chunk_reports": chunk_reports,
    }
    return timeline, stats


def _build_empty_stats(epub_word_count: int, spoken_word_count: int) -> dict[str, Any]:
    return {
        "matched_word_count": 0,
        "spoken_word_count": spoken_word_count,
        "epub_word_count": epub_word_count,
        "match_ratio": 0.0,
        "accepted_chunk_count": 0,
        "chunk_count": 0,
        "chunk_reports": [],
    }


def _build_spoken_tokens(spoken_words: list[SpokenWord]) -> tuple[list[str], list[int]]:
    tokens: list[str] = []
    token_to_spoken_index: list[int] = []
    for spoken_index, spoken_word in enumerate(spoken_words):
        normalized = normalize_word(spoken_word.word)
        if normalized.isdigit():
            numeric = int(normalized)
            if 1 <= numeric <= 100:
                normalized = int_to_words(numeric).replace(" ", "")
        if not normalized:
            continue
        tokens.append(normalized)
        token_to_spoken_index.append(spoken_index)
    return tokens, token_to_spoken_index


def _build_epub_tokens(epub_words: list[EpubWord]) -> tuple[list[str], list[int]]:
    tokens: list[str] = []
    token_to_epub_index: list[int] = []
    for epub_index, epub_word in enumerate(epub_words):
        align_tokens = epub_word.align_tokens or []
        if not align_tokens:
            normalized = normalize_word(epub_word.word)
            align_tokens = [normalized] if normalized else []
        for token in align_tokens:
            if not token:
                continue
            tokens.append(token)
            token_to_epub_index.append(epub_index)
    return tokens, token_to_epub_index


def _smooth_timeline(entries: list[TimelineEntry]) -> list[TimelineEntry]:
    if not entries:
        return entries

    smoothed: list[TimelineEntry] = []
    previous_end = 0.0
    for entry in entries:
        start = max(previous_end, entry.start)
        end = max(start, entry.end)
        if end - start > 1.5:
            end = start + 1.5
        smoothed.append(
            TimelineEntry(
                start=round(start, 3),
                end=round(end, 3),
                word=entry.word,
                spoken=entry.spoken,
                spine=entry.spine,
                cfi=entry.cfi,
            )
        )
        previous_end = smoothed[-1].end
    return smoothed
