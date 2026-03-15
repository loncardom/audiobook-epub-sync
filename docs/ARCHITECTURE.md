# Architecture Notes

## Objective

Produce a timeline JSON that the frontend can consume directly for:
- word highlighting
- click-to-seek
- playback-follow navigation

## Proposed pipeline

1. EPUB extraction
- Parse the EPUB spine in reading order.
- Remove non-content tags such as `script`, `style`, and `noscript`.
- Emit one row per visible word with:
  - source word
  - spine index
  - section href
  - CSS-like DOM path
  - word index within the element
  - normalized alignment tokens

2. Audio word extraction
- Chunk long audio into manageable windows.
- Run ASR and produce word-level timestamps.
- Normalize tokens similarly to the EPUB side.

3. Alignment
- Match spoken tokens to EPUB tokens with a monotonic alignment strategy.
- Preserve enough debug data to understand skips, low-confidence windows, and cursor drift.
- Support chunked / resumable alignment for long books.

4. Output
- Emit frontend-compatible timeline rows.
- Emit optional debug reports and intermediate JSONs.

## Existing experiments worth mining

- `../scripts/extract_epub_words.py`
  - already builds the custom locator string the frontend expects
- `../scripts/build_full_book_timeline_chunked.py`
  - shows chunked processing and a monotonic cursor strategy
- `../scripts/run_pipeline.sh`
  - documents the old end-to-end flow and external dependencies

## Output contract to preserve

The frontend currently relies on:
- `start` and `end` as seconds
- `word` as the EPUB-side token
- `spoken` optionally preserving the ASR-side token
- `spine` for diagnostics / compatibility
- `cfi` holding the custom locator string

## First implementation milestone

A good first milestone for Claude:
- implement EPUB extraction cleanly inside this package
- define a stable on-disk intermediate format for extracted EPUB words
- define a spoken-word intermediate format
- implement a placeholder aligner that can at least join exact/near-exact matches on small test clips
- write one integration test around a tiny fixture set
