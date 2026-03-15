# audiobook-epub-sync

`audiobook-epub-sync` is a CLI tool for generating the sync file consumed by the `audio-ebook-site` reader.

## Goal

Given:
- an EPUB
- an audiobook file

produce:
- a JSON timeline file that maps spoken audio back to EPUB word locations so the reader can:
  - highlight the current spoken word
  - scrub audio by clicking words
  - jump the book view to the spoken location

## Relationship to the existing workspace

This project is a clean CLI-oriented successor to the experimental scripts in the parent `ebook-voice/` directory.

Useful reference artifacts in the parent workspace:
- `scripts/extract_epub_words.py`
- `scripts/asr_words.py`
- `scripts/align_asr_to_epub.py`
- `scripts/join_timings_to_epub.py`
- `scripts/build_full_book_timeline_chunked.py`
- `book_timeline.json`
- `book_timeline_full_chunked.json`
- `epub_words.json`
- `book_words.json`
- `spoken_epub_refs.json`

Those files show the current experiments and output shape, but this package should become a standalone, documented, reusable CLI.

## Expected output format

The frontend currently expects timeline rows shaped like:

```json
{
  "start": 123.456,
  "end": 123.789,
  "word": "example",
  "spoken": "example",
  "spine": 7,
  "cfi": "spine=7;href=OEBPS/chapter.xhtml;path=html > body > p:nth-of-type(3);w=12"
}
```

Important note:
- The `cfi` field name is historical. In the current system it is not a standard EPUB CFI.
- It is a custom locator string composed of:
  - `spine=<number>`
  - `href=<section href>`
  - `path=<css-like DOM path>`
  - `w=<word index within that element>`

## Initial CLI shape

Planned command:

```bash
audiobook-epub-sync build \
  --epub /path/to/book.epub \
  --audio /path/to/book.mp3 \
  --output /path/to/book_timeline.json
```

Likely future options:
- `--chunk-seconds`
- `--asr-model`
- `--work-dir`
- `--resume`
- `--debug-dir`
- `--format json`
- `--emit-report`

## Development

Create a virtual environment and install editable dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

External tools for full timeline generation:
- `ffmpeg`
- `ffprobe`
- one ASR backend:
  - `whisper` CLI, or
  - `faster-whisper`, or
  - `openai-whisper`

Run the CLI module directly:

```bash
python -m audiobook_epub_sync.cli build --help
```

## Status

This project is now being built as a clean standalone pipeline whose sole purpose is to generate:
- `book_timeline.json`
- `epub_words.json`
- other optional debug JSON artifacts

Current implementation status:
- EPUB extraction is implemented and writes `epub_words.json` with frontend-compatible locators
- CLI orchestration and build reporting are implemented
- ASR extraction is implemented through pluggable Whisper-family backends
- generic monotonic alignment and baseline timeline emission are implemented
- timing refinement is still minimal and should be improved for production accuracy

The intended direction is a general-purpose pipeline for most books, not a collection of book-specific heuristics.
