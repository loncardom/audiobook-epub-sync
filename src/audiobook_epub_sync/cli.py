from __future__ import annotations

import argparse
from pathlib import Path

from .align import align_spoken_words_with_stats
from .audio import validate_audio_path
from .asr import extract_spoken_words
from .epub import extract_epub_words
from .models import BuildArtifacts, BuildConfig, BuildReport
from .output import write_json


def build_epub_words_output_path(config: BuildConfig) -> Path:
    return config.work_dir / "epub_words.json"


def build_spoken_words_output_path(config: BuildConfig) -> Path:
    return config.work_dir / "asr_words.json"


def build_report_output_path(config: BuildConfig) -> Path:
    return config.work_dir / "build_report.json"


def build_command(args: argparse.Namespace) -> int:
    config = BuildConfig(
        epub_path=Path(args.epub).expanduser().resolve(),
        audio_path=Path(args.audio).expanduser().resolve(),
        output_path=Path(args.output).expanduser().resolve(),
        work_dir=Path(args.work_dir).expanduser().resolve(),
        chunk_seconds=args.chunk_seconds,
        asr_model=args.asr_model,
        emit_report=not args.no_report,
    )

    if not config.epub_path.exists():
        raise SystemExit(f"EPUB file not found: {config.epub_path}")
    validate_audio_path(config.audio_path)
    config.work_dir.mkdir(parents=True, exist_ok=True)

    epub_words = extract_epub_words(config.epub_path)
    artifacts = BuildArtifacts(
        epub_words_path=build_epub_words_output_path(config),
        spoken_words_path=build_spoken_words_output_path(config),
        timeline_path=config.output_path,
        report_path=build_report_output_path(config) if config.emit_report else None,
    )
    write_json(artifacts.epub_words_path, [word.to_dict() for word in epub_words])

    report_status = "success"
    report_message = "Build completed."
    report_artifacts = {
        "epub_words": str(artifacts.epub_words_path),
    }
    report_stats = {
        "epub_word_count": len(epub_words),
        "chunk_seconds": config.chunk_seconds,
        "asr_model": config.asr_model,
    }

    try:
        spoken_words = extract_spoken_words(config)
        write_json(artifacts.spoken_words_path, [word.to_dict() for word in spoken_words])
        timeline_entries, alignment_stats = align_spoken_words_with_stats(epub_words, spoken_words)
        write_json(artifacts.timeline_path, [entry.to_dict() for entry in timeline_entries])
        report_artifacts["spoken_words"] = str(artifacts.spoken_words_path)
        report_artifacts["timeline"] = str(artifacts.timeline_path)
        report_stats["spoken_word_count"] = len(spoken_words)
        report_stats["timeline_entry_count"] = len(timeline_entries)
        report_stats["alignment_match_ratio"] = alignment_stats["match_ratio"]
        report_stats["accepted_chunk_count"] = alignment_stats["accepted_chunk_count"]
        report_stats["chunk_count"] = alignment_stats["chunk_count"]
        report_stats["chunk_reports"] = alignment_stats["chunk_reports"]
        report_stats["repaired_word_count"] = alignment_stats["repaired_word_count"]
        report_stats["repaired_gap_count"] = alignment_stats["repaired_gap_count"]
        report_stats["unrepaired_short_gap_count"] = alignment_stats["unrepaired_short_gap_count"]
        report_stats["repair_examples"] = alignment_stats["repair_examples"]
    except Exception as exc:
        report_status = "partial"
        report_message = (
            "EPUB extraction completed, but ASR/alignment did not finish. "
            f"Reason: {exc}"
        )
        report_stats["spoken_word_count"] = 0
        report_stats["timeline_entry_count"] = 0
        report_stats["alignment_match_ratio"] = 0.0
        report_stats["repaired_word_count"] = 0
        report_stats["repaired_gap_count"] = 0
        report_stats["unrepaired_short_gap_count"] = 0
        report_stats["repair_examples"] = []

    report = BuildReport(
        status=report_status,
        message=report_message,
        inputs={
            "epub": str(config.epub_path),
            "audio": str(config.audio_path),
            "output": str(config.output_path),
        },
        artifacts=report_artifacts,
        stats=report_stats,
    )
    if artifacts.report_path is not None:
        write_json(artifacts.report_path, report.to_dict())

    print(f"Wrote EPUB words to {artifacts.epub_words_path}")
    if artifacts.spoken_words_path is not None and artifacts.spoken_words_path.exists():
        print(f"Wrote ASR words to {artifacts.spoken_words_path}")
    if artifacts.timeline_path is not None and artifacts.timeline_path.exists():
        print(f"Wrote timeline to {artifacts.timeline_path}")
    if artifacts.report_path is not None:
        print(f"Wrote build report to {artifacts.report_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="audiobook-epub-sync")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Align an EPUB and audiobook into a timeline JSON")
    build.add_argument("--epub", required=True, help="Path to the EPUB file")
    build.add_argument("--audio", required=True, help="Path to the audiobook media file")
    build.add_argument("--output", required=True, help="Path to write the timeline JSON")
    build.add_argument("--work-dir", default="./work", help="Directory for intermediate artifacts")
    build.add_argument("--chunk-seconds", type=int, default=300, help="Chunk size for long audio")
    build.add_argument("--asr-model", default="base", help="ASR model identifier")
    build.add_argument("--no-report", action="store_true", help="Disable extra report emission")
    build.set_defaults(func=build_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
