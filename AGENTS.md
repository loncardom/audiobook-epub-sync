# AGENTS.md

## Project intent

This repository is for a standalone CLI that generates the sync JSON consumed by `audio-ebook-site`.

Inputs:
- EPUB
- audiobook audio file

Primary output:
- timeline JSON with rows of `{start, end, word, spoken?, spine?, cfi}`

## Context from sibling project

The sibling app `audio-ebook-site/` already consumes this output.
The current frontend assumptions are:
- the `cfi` field is actually a custom locator string, not a standard EPUB CFI
- locator shape: `spine=...;href=...;path=...;w=...`
- audio sync is word-oriented first, with DOM-based highlighting and click-to-seek

## Existing experimental references

The parent `ebook-voice/` directory contains exploratory scripts and artifacts.
Treat them as reference material to mine for logic, not as final architecture.

High-value reference files:
- `../scripts/extract_epub_words.py`
- `../scripts/asr_words.py`
- `../scripts/align_asr_to_epub.py`
- `../scripts/join_timings_to_epub.py`
- `../scripts/build_full_book_timeline_chunked.py`
- `../book_timeline.json`
- `../book_timeline_full_chunked.json`
- `../epub_words.json`
- `../book_words.json`

## Working conventions

- Prefer a clean package architecture over copying scripts verbatim.
- Preserve compatibility with the current frontend output contract unless explicitly changing both projects together.
- Favor typed models and small, testable pipeline stages.
- Treat large audio files and generated artifacts as inputs/outputs, not source-controlled implementation details.
- Keep the default UX CLI-first and local-first.

## Near-term implementation target

The first useful version should:
1. extract ordered EPUB words with DOM locators
2. produce spoken-word timestamps from audio
3. align spoken words back to EPUB words
4. emit a frontend-compatible timeline JSON
5. optionally emit a debug report and intermediate files

## Suggested package boundaries

- `epub.py`: EPUB parsing and locator extraction
- `audio.py`: duration, chunking, transcoding helpers
- `asr.py`: spoken-word extraction
- `align.py`: matching spoken words to EPUB words
- `models.py`: typed dataclasses / schemas
- `output.py`: timeline JSON + reports
- `cli.py`: command entrypoint
