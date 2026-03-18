import json
from pathlib import Path

from audiobook_epub_sync import cli
from audiobook_epub_sync.cli import build_parser
from audiobook_epub_sync.epub import extract_epub_words
from audiobook_epub_sync.models import EpubWord, SpokenWord, TimelineEntry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EPUB_PATH = PROJECT_ROOT / "_OceanofPDF.com_The_Last_Question_-_Isaac_Asimov.epub"
AUDIO_PATH = PROJECT_ROOT / "The Last Question - Isaac Asimov - Read by Leonard Nimoy - Cool Psycho Facts (128k).mp3"


def test_build_parser_has_build_command() -> None:
    parser = build_parser()
    args = parser.parse_args([
        "build",
        "--epub",
        "book.epub",
        "--audio",
        "book.mp3",
        "--output",
        "book_timeline.json",
    ])
    assert args.command == "build"


def test_extract_epub_words_returns_locator_rows() -> None:
    words = extract_epub_words(EPUB_PATH)

    assert words
    first_word = words[0]
    assert first_word.word
    assert first_word.cfi.startswith("spine=")
    assert "href=" in first_word.cfi
    assert "path=" in first_word.cfi
    assert "w=" in first_word.cfi


def test_build_command_writes_epub_words_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "extract_epub_words",
        lambda _path: [
            EpubWord(
                index=0,
                word="Hello",
                spine=0,
                href="chapter.xhtml",
                path="html > body > p",
                cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=0",
                align_tokens=["hello"],
            )
        ],
    )
    monkeypatch.setattr(
        cli,
        "extract_spoken_words",
        lambda _config: [
            SpokenWord(index=0, word="Hello", start=0.0, end=0.2, chunk_index=0)
        ],
    )
    monkeypatch.setattr(
        cli,
        "align_spoken_words_with_stats",
        lambda _epub_words, _spoken_words: (
            [
                TimelineEntry(
                    start=0.0,
                    end=0.2,
                    word="Hello",
                    spoken="Hello",
                    spine=0,
                    cfi="spine=0;href=chapter.xhtml;path=html > body > p;w=0",
                )
            ],
            {
                "match_ratio": 1.0,
                "accepted_chunk_count": 1,
                "chunk_count": 1,
                "chunk_reports": [],
                "repaired_word_count": 0,
                "repaired_gap_count": 0,
                "unrepaired_short_gap_count": 0,
                "repair_examples": [],
            },
        ),
    )

    parser = build_parser()
    args = parser.parse_args([
        "build",
        "--epub",
        str(EPUB_PATH),
        "--audio",
        str(AUDIO_PATH),
        "--output",
        str(tmp_path / "book_timeline.json"),
        "--work-dir",
        str(tmp_path / "work"),
    ])

    exit_code = args.func(args)

    epub_words_path = tmp_path / "work" / "epub_words.json"
    report_path = tmp_path / "work" / "build_report.json"

    assert exit_code == 0
    assert epub_words_path.exists()
    assert report_path.exists()

    epub_words = json.loads(epub_words_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert isinstance(epub_words, list)
    assert epub_words
    assert report["status"] == "success"
    assert report["stats"]["timeline_entry_count"] == 1
