from __future__ import annotations

import difflib
from typing import Any

from .models import EpubWord, SpokenWord, TimelineEntry
from .text import normalize_alignment_tokens


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

    exact_matches: list[tuple[int, int]] = []
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

        exact_matches.append((spoken_index, epub_index))
        timeline.append(
            TimelineEntry(
                start=spoken_word.start,
                end=spoken_word.end,
                word=epub_word.word,
                spoken=spoken_word.word,
                spine=epub_word.spine,
                cfi=epub_word.cfi,
                repaired=False,
            )
        )
        previous_end = spoken_word.end
        chunk_counts[chunk_index]["matched_words"] += 1

    for spoken_word in spoken_words:
        chunk_index = spoken_word.chunk_index if spoken_word.chunk_index is not None else 0
        chunk_counts.setdefault(chunk_index, {"spoken_words": 0, "matched_words": 0})
        chunk_counts[chunk_index]["spoken_words"] += 1

    repaired_entries, repair_stats = _repair_short_gaps(exact_matches, epub_words, spoken_words)
    timeline.extend(repaired_entries)
    timeline.sort(key=lambda entry: (entry.start, entry.end, entry.repaired))
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
        "repaired_word_count": repair_stats["repaired_word_count"],
        "repaired_gap_count": repair_stats["repaired_gap_count"],
        "unrepaired_short_gap_count": repair_stats["unrepaired_short_gap_count"],
        "repair_examples": repair_stats["repair_examples"],
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
        "repaired_word_count": 0,
        "repaired_gap_count": 0,
        "unrepaired_short_gap_count": 0,
        "repair_examples": [],
    }


def _build_spoken_tokens(spoken_words: list[SpokenWord]) -> tuple[list[str], list[int]]:
    tokens: list[str] = []
    token_to_spoken_index: list[int] = []
    for spoken_index, spoken_word in enumerate(spoken_words):
        for token in normalize_alignment_tokens(spoken_word.word):
            if not token:
                continue
            tokens.append(token)
            token_to_spoken_index.append(spoken_index)
    return tokens, token_to_spoken_index


def _build_epub_tokens(epub_words: list[EpubWord]) -> tuple[list[str], list[int]]:
    tokens: list[str] = []
    token_to_epub_index: list[int] = []
    for epub_index, epub_word in enumerate(epub_words):
        align_tokens = epub_word.align_tokens or normalize_alignment_tokens(epub_word.word)
        for token in align_tokens:
            if not token:
                continue
            tokens.append(token)
            token_to_epub_index.append(epub_index)
    return tokens, token_to_epub_index


def _repair_short_gaps(
    exact_matches: list[tuple[int, int]],
    epub_words: list[EpubWord],
    spoken_words: list[SpokenWord],
) -> tuple[list[TimelineEntry], dict[str, Any]]:
    repaired_entries: list[TimelineEntry] = []
    repaired_gap_count = 0
    unrepaired_short_gap_count = 0
    repair_examples: list[dict[str, Any]] = []

    for index in range(len(exact_matches) - 1):
        left_spoken_index, left_epub_index = exact_matches[index]
        right_spoken_index, right_epub_index = exact_matches[index + 1]

        missing_epub_count = right_epub_index - left_epub_index - 1
        spoken_gap = right_spoken_index - left_spoken_index - 1

        if missing_epub_count <= 0 or missing_epub_count > 4:
            continue

        left_spoken = spoken_words[left_spoken_index]
        right_spoken = spoken_words[right_spoken_index]
        left_chunk = left_spoken.chunk_index if left_spoken.chunk_index is not None else 0
        right_chunk = right_spoken.chunk_index if right_spoken.chunk_index is not None else 0
        if left_chunk != right_chunk:
            unrepaired_short_gap_count += 1
            continue

        gap_spoken_words = spoken_words[left_spoken_index + 1 : right_spoken_index]
        if spoken_gap > missing_epub_count + 2:
            unrepaired_short_gap_count += 1
            continue

        gap_start = left_spoken.end
        gap_end = right_spoken.start
        if gap_spoken_words:
            gap_start = max(
                gap_start,
                gap_spoken_words[0].segment_start
                if gap_spoken_words[0].segment_start is not None
                else gap_spoken_words[0].start,
            )
            gap_end = min(
                gap_end,
                gap_spoken_words[-1].segment_end
                if gap_spoken_words[-1].segment_end is not None
                else gap_spoken_words[-1].end,
            )
        gap_duration = gap_end - gap_start
        if gap_duration < 0.08 or gap_duration > 1.8:
            unrepaired_short_gap_count += 1
            continue

        raw_missing_words = epub_words[left_epub_index + 1 : right_epub_index]
        missing_words = [
            word
            for word in raw_missing_words
            if word.align_tokens or normalize_alignment_tokens(word.word)
        ]
        if not missing_words:
            continue

        missing_tokens = _flatten_alignment_tokens(missing_words)
        gap_tokens = _flatten_alignment_tokens(gap_spoken_words)
        if not _is_repair_candidate(
            missing_tokens=missing_tokens,
            gap_tokens=gap_tokens,
            missing_word_count=len(missing_words),
        ):
            unrepaired_short_gap_count += 1
            continue

        repaired_gap_count += 1
        weights = [_timing_weight(word) for word in missing_words]
        total_weight = sum(weights) or len(missing_words)
        cursor = gap_start

        for missing_index, (epub_word, weight) in enumerate(zip(missing_words, weights)):
            share = gap_duration * (weight / total_weight)
            start = cursor
            end = gap_end if missing_index == len(missing_words) - 1 else min(gap_end, cursor + share)
            repaired_entries.append(
                TimelineEntry(
                    start=start,
                    end=end,
                    word=epub_word.word,
                    spoken=None,
                    spine=epub_word.spine,
                    cfi=epub_word.cfi,
                    repaired=True,
                )
            )
            cursor = end

        if len(repair_examples) < 10:
            repair_examples.append(
                {
                    "left_word": epub_words[left_epub_index].word,
                    "repaired_words": [word.word for word in missing_words],
                    "right_word": epub_words[right_epub_index].word,
                    "gap_start": round(gap_start, 3),
                    "gap_end": round(gap_end, 3),
                }
            )

    return repaired_entries, {
        "repaired_word_count": len(repaired_entries),
        "repaired_gap_count": repaired_gap_count,
        "unrepaired_short_gap_count": unrepaired_short_gap_count,
        "repair_examples": repair_examples,
    }


def _timing_weight(word: EpubWord) -> int:
    tokens = word.align_tokens or normalize_alignment_tokens(word.word)
    total_length = sum(len(token) for token in tokens if token)
    return max(1, total_length)


def _flatten_alignment_tokens(words: list[EpubWord] | list[SpokenWord]) -> list[str]:
    tokens: list[str] = []
    for word in words:
        if isinstance(word, EpubWord):
            next_tokens = word.align_tokens or normalize_alignment_tokens(word.word)
        else:
            next_tokens = normalize_alignment_tokens(word.word)
        tokens.extend(token for token in next_tokens if token)
    return tokens


def _is_repair_candidate(
    missing_tokens: list[str],
    gap_tokens: list[str],
    missing_word_count: int,
) -> bool:
    if not missing_tokens:
        return False

    if not gap_tokens:
        return missing_word_count <= 3

    token_ratio = difflib.SequenceMatcher(a=gap_tokens, b=missing_tokens, autojunk=False).ratio()
    phrase_ratio = difflib.SequenceMatcher(
        a=" ".join(gap_tokens),
        b=" ".join(missing_tokens),
        autojunk=False,
    ).ratio()
    return token_ratio >= 0.45 or phrase_ratio >= 0.72


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
                repaired=entry.repaired,
            )
        )
        previous_end = smoothed[-1].end
    return smoothed
