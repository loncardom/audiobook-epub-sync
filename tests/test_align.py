from audiobook_epub_sync.align import align_spoken_words
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
