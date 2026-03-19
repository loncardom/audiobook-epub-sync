# audiobook-epub-sync

`audiobook-epub-sync` is a small local-first CLI for aligning an audiobook to an EPUB and emitting a word timeline JSON that a reader can use for:

- word highlighting
- click-to-seek
- page jumps while audio plays or scrubs

The project exists to generate one thing well: a frontend-friendly `book_timeline.json`.

## What It Produces

The primary output is a JSON array of rows shaped like:

```json
{
  "start": 123.456,
  "end": 123.789,
  "word": "example",
  "spoken": "example",
  "spine": 7,
  "cfi": "spine=7;href=OEBPS/chapter.xhtml;path=html > body > p:nth-of-type(3);w=12",
  "repaired": false
}
```

Notes:

- `cfi` is a historical field name. It is not a standard EPUB CFI.
- In this project, `cfi` is a custom locator string composed of:
  - `spine=<number>`
  - `href=<section href>`
  - `path=<css-like DOM path>`
  - `w=<word index within that element>`
- `repaired: true` means the word was recovered by the post-alignment repair pass rather than directly matched from ASR output.

## How It Works

The pipeline is intentionally simple and local:

1. Extract visible words from the EPUB in reading order.
2. Preserve stable per-word locators for the frontend.
3. Transcribe the audiobook into word timestamps with a Whisper-family backend.
4. Align spoken words back onto EPUB words using monotonic text alignment.
5. Repair short missed-word gaps conservatively.
6. Emit timeline and debug artifacts.

The EPUB text is the source of truth for displayed words. The audio provides timing.

## Repair Strategy

ASR regularly misses short words, proper nouns, contractions, and numbers. Without repair, highlighting drifts because the reader jumps from one matched word to the next and skips the missing words entirely.

This project includes a conservative repair pass after primary alignment.

What it does:

- fills short unmatched EPUB gaps between strong neighboring anchors
- uses the known timing window between those anchors
- distributes timing across the missing words without breaking monotonic order
- performs short fuzzy recovery for small local mismatches when the surrounding context is strong
- normalizes some numeric forms such as `14` and `fourteen`

What it does not do:

- invent long missing passages
- try to force every unmatched phrase into the timeline
- use book-specific anchor phrases or title-specific heuristics

That tradeoff is deliberate. The repair layer is meant to improve practical sync quality while staying general across books.

## Installation

Create a virtual environment and install the package:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Required Python dependencies are declared in `pyproject.toml`.

External tools:

- `ffmpeg`
- `ffprobe`
- one Whisper-family ASR backend:
  - `whisper` CLI, or
  - `faster-whisper`, or
  - `openai-whisper`

## CLI Usage

After installation, use the console script:

```bash
audiobook-epub-sync build \
  --epub /path/to/book.epub \
  --audio /path/to/book.mp3 \
  --output /path/to/book_timeline.json \
  --work-dir /path/to/work
```

You can also run the module directly:

```bash
python -m audiobook_epub_sync.cli build \
  --epub /path/to/book.epub \
  --audio /path/to/book.mp3 \
  --output /path/to/book_timeline.json \
  --work-dir /path/to/work
```

### CLI Options

- `--epub`: input EPUB
- `--audio`: input audiobook media file
- `--output`: output timeline JSON path
- `--work-dir`: directory for intermediate artifacts and report output
- `--chunk-seconds`: audio chunk size for ASR, default `300`
- `--asr-model`: Whisper model identifier, default `base`
- `--no-report`: disable `build_report.json`

### Example

```bash
audiobook-epub-sync build \
  --epub "samples/the last question/_OceanofPDF.com_The_Last_Question_-_Isaac_Asimov.epub" \
  --audio "samples/the last question/The Last Question Audiobook, by Isaac Asimov, read by Jack Fox - Mundum Visum (128k).mp3" \
  --output "samples/the last question/book_timeline.json" \
  --work-dir "samples/the last question/work"
```

## Output Files

A normal run writes:

- `book_timeline.json`: final frontend timeline
- `work/epub_words.json`: extracted EPUB words with locators
- `work/asr_words.json`: transcribed spoken words with timestamps
- `work/build_report.json`: summary metrics and warnings

## Reading The Report

The build report includes two metrics that should be read together:

- `alignment_match_ratio`: how many spoken words were aligned
- `epub_coverage_ratio`: how much of the EPUB is represented in the emitted timeline

That distinction matters.

A pair can have a high `alignment_match_ratio` while still being a poor real-world match if the audiobook covers only part of the EPUB. In those cases the report message includes a warning that the audiobook may not match the full EPUB text.

Useful report fields:

- `spoken_word_count`
- `timeline_entry_count`
- `matched_epub_word_count`
- `alignment_match_ratio`
- `epub_coverage_ratio`
- `repaired_word_count`
- `repaired_gap_count`
- `unrepaired_short_gap_count`

## Results

This repo was tested against three real audiobook/EPUB pairs.

- `The Celebrated Jumping Frog of Calaveras County`
  - audiobook coverage looked healthy
  - `alignment_match_ratio = 0.9303`
  - `epub_coverage_ratio = 0.9407`
  - `repaired_word_count = 129`
- `The Gift of the Magi`
  - spoken-word alignment looked high, but the pair did not behave like a full-text match
  - `alignment_match_ratio = 0.9672`
  - `epub_coverage_ratio = 0.3929`
  - `repaired_word_count = 41`
  - the report correctly warns that the audiobook may not match the full EPUB text

- `The Last Question`
  - `alignment_match_ratio = 0.9622`
  - `epub_coverage_ratio = 0.9629`
  - `repaired_word_count = 125`

The public-domain audiobook tests above are based on works available through LibriVox and public-domain ebook sources.

## Limitations

- This is a practical alignment tool, not a phoneme-level forced aligner.
- Accuracy depends heavily on how closely the audiobook narration matches the EPUB text.
- Chapter headings, front matter, OCR noise, and alternate spoken forms can still create gaps.
- The repair pass helps noticeably on short misses, but it is intentionally conservative.
- A very high spoken-word match ratio does not guarantee full-book coverage. Check `epub_coverage_ratio`.

## Frontend Compatibility

The output format is intentionally compatible with the sibling `audio-ebook-site` reader in this workspace.

In particular:

- the timeline is word-oriented
- the `cfi` field carries the custom locator format expected by the reader
- repaired words remain compatible with the same timeline contract

## Credits

- Audiobook recordings and public-domain source material used for testing: LibriVox and public-domain ebook sources
- Build and implementation assistance: OpenAI ChatGPT Codex
