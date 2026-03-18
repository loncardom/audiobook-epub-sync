from audiobook_epub_sync.align import align_spoken_words, align_spoken_words_with_stats
from audiobook_epub_sync.models import EpubWord, SpokenWord


def test_align_spoken_words_matches_monotonic_words() -> None:
    epub_words = [
        EpubWord(
            index=0,
            word="Hello",
            spine=0,
            href="chapter.xhtml",
            path="html > body > p",
            cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=0",
            align_tokens=["hello"],
        ),
        EpubWord(
            index=1,
            word="world",
            spine=0,
            href="chapter.xhtml",
            path="html > body > p",
            cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=1",
            align_tokens=["world"],
        ),
    ]
    spoken_words = [
        SpokenWord(index=0, word="Hello", start=0.0, end=0.3),
        SpokenWord(index=1, word="world", start=0.3, end=0.6),
    ]

    timeline = align_spoken_words(epub_words, spoken_words)

    assert len(timeline) == 2
    assert timeline[0].word == "Hello"
    assert timeline[1].word == "world"
    assert timeline[0].start == 0.0
    assert timeline[1].end == 0.6


def test_align_spoken_words_repairs_short_gap_between_exact_anchors() -> None:
    epub_words = [
        EpubWord(
            index=0,
            word="But",
            spine=0,
            href="chapter.xhtml",
            path="html > body > p",
            cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=0",
            align_tokens=["but"],
        ),
        EpubWord(
            index=1,
            word="slowly",
            spine=0,
            href="chapter.xhtml",
            path="html > body > p",
            cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=1",
            align_tokens=["slowly"],
        ),
        EpubWord(
            index=2,
            word="Multivac",
            spine=0,
            href="chapter.xhtml",
            path="html > body > p",
            cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=2",
            align_tokens=["multivac"],
        ),
        EpubWord(
            index=3,
            word="learned",
            spine=0,
            href="chapter.xhtml",
            path="html > body > p",
            cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=3",
            align_tokens=["learned"],
        ),
    ]
    spoken_words = [
        SpokenWord(index=0, word="But", start=0.0, end=0.2, chunk_index=0),
        SpokenWord(index=1, word="slowly", start=0.2, end=0.4, chunk_index=0),
        SpokenWord(index=2, word="learned", start=0.9, end=1.1, chunk_index=0),
    ]

    timeline, stats = align_spoken_words_with_stats(epub_words, spoken_words)

    assert [entry.word for entry in timeline] == ["But", "slowly", "Multivac", "learned"]
    repaired_entry = timeline[2]
    assert repaired_entry.repaired is True
    assert repaired_entry.spoken is None
    assert 0.4 <= repaired_entry.start <= repaired_entry.end <= 0.9
    assert stats["repaired_word_count"] == 1
    assert stats["repaired_gap_count"] == 1


def test_align_spoken_words_matches_spoken_number_to_epub_digit() -> None:
    epub_words = [
        EpubWord(
            index=0,
            word="14",
            spine=0,
            href="chapter.xhtml",
            path="html > body > p",
            cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=0",
            align_tokens=["fourteen"],
        ),
    ]
    spoken_words = [
        SpokenWord(index=0, word="fourteen", start=0.0, end=0.3, chunk_index=0),
    ]

    timeline = align_spoken_words(epub_words, spoken_words)

    assert len(timeline) == 1
    assert timeline[0].word == "14"


def test_align_spoken_words_repairs_fuzzy_gap_with_misheard_spoken_word() -> None:
    epub_words = [
        EpubWord(
            index=0,
            word="But",
            spine=0,
            href="chapter.xhtml",
            path="html > body > p",
            cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=0",
            align_tokens=["but"],
        ),
        EpubWord(
            index=1,
            word="Multivac",
            spine=0,
            href="chapter.xhtml",
            path="html > body > p",
            cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=1",
            align_tokens=["multivac"],
        ),
        EpubWord(
            index=2,
            word="learned",
            spine=0,
            href="chapter.xhtml",
            path="html > body > p",
            cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=2",
            align_tokens=["learned"],
        ),
    ]
    spoken_words = [
        SpokenWord(index=0, word="But", start=0.0, end=0.2, chunk_index=0, segment_start=0.0, segment_end=0.2),
        SpokenWord(index=1, word="Moltivac", start=0.2, end=0.5, chunk_index=0, segment_start=0.2, segment_end=0.5),
        SpokenWord(index=2, word="learned", start=0.5, end=0.7, chunk_index=0, segment_start=0.5, segment_end=0.7),
    ]

    timeline, stats = align_spoken_words_with_stats(epub_words, spoken_words)

    assert [entry.word for entry in timeline] == ["But", "Multivac", "learned"]
    assert timeline[1].repaired is True
    assert stats["repaired_word_count"] == 1
