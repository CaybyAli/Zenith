from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from statistics import mean
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from core.speech_foundation import (
    build_silence_gaps,
    build_speech_segments,
    find_phrase_occurrences,
    normalize_word_entries,
    speech_coverage_percent,
)


def _run_command(command: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError("Command failed: " + " ".join(command) + "\n" + message)
    return completed


def _resolve_tool(configured: str | None, fallback_windows: str, plain_name: str) -> str:
    if configured:
        return configured

    fallback_path = Path(fallback_windows)
    if fallback_path.exists():
        return str(fallback_path)

    return plain_name


def _default_whisperx_python() -> str:
    if os.getenv("ZENITH_WHISPERX_PYTHON"):
        return os.environ["ZENITH_WHISPERX_PYTHON"]

    candidate = REPO_ROOT / ".venv_whisperx_p5_2" / "Scripts" / "python.exe"
    if candidate.exists():
        return str(candidate)

    return str(REPO_ROOT / ".venv_whisperx_p5_2" / "bin" / "python")


def _default_whisperx_bridge() -> str:
    if os.getenv("ZENITH_WHISPERX_BRIDGE"):
        return os.environ["ZENITH_WHISPERX_BRIDGE"]

    return str(REPO_ROOT / "core" / "whisperx_bridge_transcribe.py")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _inspect_audio_streams(ffprobe: str, video_path: Path) -> tuple[list[dict[str, Any]], float]:
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(video_path),
    ]
    completed = _run_command(command, timeout=60)
    payload = json.loads(completed.stdout or "{}")

    format_payload = payload.get("format") or {}
    media_duration = _safe_float(format_payload.get("duration"), 0.0)

    audio_streams: list[dict[str, Any]] = []
    for audio_ordinal, stream in enumerate(payload.get("streams") or []):
        if stream.get("codec_type") != "audio":
            continue

        duration = _safe_float(stream.get("duration"), media_duration)
        audio_streams.append(
            {
                "audio_ordinal": audio_ordinal,
                "stream_index": int(stream.get("index")),
                "codec": str(stream.get("codec_name") or "unknown"),
                "channels": int(stream.get("channels") or 0),
                "sample_rate": str(stream.get("sample_rate") or "unknown"),
                "duration_seconds": duration,
            }
        )

    return audio_streams, media_duration


def _extract_audio_stream(
    ffmpeg: str,
    video_path: Path,
    output_path: Path,
    *,
    stream_index: int,
    start_seconds: float | None = None,
    duration_seconds: float | None = None,
) -> None:
    command = [ffmpeg, "-y", "-v", "error"]

    if start_seconds is not None:
        command.extend(["-ss", str(start_seconds)])

    command.extend(["-i", str(video_path)])

    if duration_seconds is not None:
        command.extend(["-t", str(duration_seconds)])

    command.extend(
        [
            "-map",
            f"0:{stream_index}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output_path),
        ]
    )

    _run_command(command, timeout=900)


def _run_whisperx_bridge(
    whisperx_python: str,
    bridge_path: str,
    input_path: Path,
    output_path: Path,
    *,
    model: str,
) -> dict[str, Any]:
    command = [
        whisperx_python,
        bridge_path,
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--model",
        model,
    ]

    _run_command(command, timeout=7200)

    if not output_path.exists():
        raise RuntimeError(f"WhisperX report missing: {output_path}")

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    if str(payload.get("status") or "").lower() != "ok":
        raise RuntimeError(
            "WhisperX failed: "
            + str(payload.get("error") or payload.get("message") or payload)
        )

    return payload


def _words_from_whisperx_report(report: dict[str, Any], *, offset_seconds: float = 0.0) -> list[dict[str, Any]]:
    raw_words: list[dict[str, Any]] = []

    for segment in report.get("segments") or []:
        for word in segment.get("words") or []:
            text = str(word.get("word") or word.get("text") or "").strip()
            start = word.get("start")
            end = word.get("end")

            if not text or start is None or end is None:
                continue

            raw_words.append(
                {
                    "word": text,
                    "start_seconds": _safe_float(start) + offset_seconds,
                    "end_seconds": _safe_float(end) + offset_seconds,
                    "confidence": word.get("probability"),
                }
            )

    return normalize_word_entries(raw_words)


def _text_from_report(report: dict[str, Any], *, max_chars: int = 260) -> str:
    parts = []
    for segment in report.get("segments") or []:
        text = str(segment.get("text") or "").strip()
        if text:
            parts.append(text)

    text = " ".join(parts).strip()
    text = " ".join(text.split())

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + " ..."


def _mean_confidence(words: list[dict[str, Any]]) -> float | None:
    values = [
        float(word["confidence"])
        for word in words
        if word.get("confidence") is not None
    ]
    if not values:
        return None

    return round(mean(values), 4)


def _parse_samples(value: str) -> list[tuple[float, float]]:
    samples: list[tuple[float, float]] = []

    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue

        if ":" not in item:
            raise ValueError("Sample format must be start:duration,start:duration")

        start_text, duration_text = item.split(":", 1)
        start = float(start_text.strip())
        duration = float(duration_text.strip())

        if start < 0 or duration <= 0:
            raise ValueError("Sample start must be >= 0 and duration must be > 0")

        samples.append((start, duration))

    if not samples:
        raise ValueError("At least one sample window is required")

    return samples


def _probe_tracks(
    *,
    video_path: Path,
    audio_streams: list[dict[str, Any]],
    samples: list[tuple[float, float]],
    ffmpeg: str,
    whisperx_python: str,
    bridge_path: str,
    model: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="zenith_speech_1_probe_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)

        for stream in audio_streams:
            all_words: list[dict[str, Any]] = []
            sample_texts: list[str] = []
            errors: list[str] = []

            for sample_index, (sample_start, sample_duration) in enumerate(samples, start=1):
                sample_wav = temp_dir / f"stream_{stream['stream_index']}_sample_{sample_index}.wav"
                sample_report = temp_dir / f"stream_{stream['stream_index']}_sample_{sample_index}.json"

                try:
                    _extract_audio_stream(
                        ffmpeg,
                        video_path,
                        sample_wav,
                        stream_index=stream["stream_index"],
                        start_seconds=sample_start,
                        duration_seconds=sample_duration,
                    )
                    report = _run_whisperx_bridge(
                        whisperx_python,
                        bridge_path,
                        sample_wav,
                        sample_report,
                        model=model,
                    )
                    words = _words_from_whisperx_report(report, offset_seconds=sample_start)
                    all_words.extend(words)
                    sample_texts.append(_text_from_report(report))
                except Exception as exc:
                    errors.append(f"sample_{sample_index}: {exc}")

            confidence = _mean_confidence(all_words)
            confidence_for_score = confidence if confidence is not None else 0.5
            word_count = len(all_words)
            score = round(word_count * confidence_for_score, 4)

            rows.append(
                {
                    **stream,
                    "word_count": word_count,
                    "mean_confidence": confidence,
                    "selection_score": score,
                    "sample_text": " | ".join(text for text in sample_texts if text).strip(),
                    "errors": errors,
                }
            )

    rows.sort(key=lambda row: (row["selection_score"], row["word_count"]), reverse=True)
    return rows


def _format_confidence(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _phrase_lines(words: list[dict[str, Any]], phrase: str) -> list[str]:
    matches = find_phrase_occurrences(words, phrase)

    if not matches:
        return [f"- {phrase}: NOT_FOUND"]

    lines = [f"- {phrase}: FOUND"]
    for match_index, match in enumerate(matches, start=1):
        entries = [
            f"{word['word']}[{word['start_seconds']:.3f}-{word['end_seconds']:.3f}]"
            for word in match
        ]
        lines.append(f"  {match_index}. " + " ".join(entries))

    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SPEECH-1 WhisperX track probe + full word transcript")
    parser.add_argument("--video", required=True, help="Path to Fortnite test video")
    parser.add_argument("--out-dir", default="reports/speech_1_transcript")
    parser.add_argument("--model", default="base")
    parser.add_argument("--samples", default="60:45,300:45")
    parser.add_argument("--merge-gap", type=float, default=0.3)
    parser.add_argument("--force-stream-index", type=int, default=None)
    parser.add_argument("--ffmpeg", default=None)
    parser.add_argument("--ffprobe", default=None)
    parser.add_argument("--whisperx-python", default=None)
    parser.add_argument("--whisperx-bridge", default=None)
    args = parser.parse_args(argv)

    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = _resolve_tool(args.ffmpeg, r"D:\Tools\ffmpeg\bin\ffmpeg.exe", "ffmpeg")
    ffprobe = _resolve_tool(args.ffprobe, r"D:\Tools\ffmpeg\bin\ffprobe.exe", "ffprobe")
    whisperx_python = args.whisperx_python or _default_whisperx_python()
    bridge_path = args.whisperx_bridge or _default_whisperx_bridge()
    samples = _parse_samples(args.samples)

    audio_streams, media_duration = _inspect_audio_streams(ffprobe, video_path)

    if not audio_streams:
        raise RuntimeError("No audio streams found")

    probe_rows = _probe_tracks(
        video_path=video_path,
        audio_streams=audio_streams,
        samples=samples,
        ffmpeg=ffmpeg,
        whisperx_python=whisperx_python,
        bridge_path=bridge_path,
        model=args.model,
    )

    if args.force_stream_index is not None:
        selected_row = next(
            (row for row in probe_rows if row["stream_index"] == args.force_stream_index),
            None,
        )
        if selected_row is None:
            raise RuntimeError(f"Forced stream index not found: {args.force_stream_index}")
        selection_reason = "forced_by_cli_after_manual_review"
    else:
        selected_row = probe_rows[0]
        selection_reason = "highest_probe_selection_score_word_count_x_confidence"

    if selected_row["word_count"] <= 0:
        raise RuntimeError("Selected stream has no word-level timestamps. SPEECH-1 cannot pass.")

    with tempfile.TemporaryDirectory(prefix="zenith_speech_1_full_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        full_wav = temp_dir / f"selected_stream_{selected_row['stream_index']}_full.wav"
        full_report = temp_dir / "selected_stream_full_whisperx.json"

        _extract_audio_stream(
            ffmpeg,
            video_path,
            full_wav,
            stream_index=selected_row["stream_index"],
        )

        full_payload = _run_whisperx_bridge(
            whisperx_python,
            bridge_path,
            full_wav,
            full_report,
            model=args.model,
        )

        words = _words_from_whisperx_report(full_payload)

    if not words:
        raise RuntimeError("Full WhisperX run produced no word-level timestamps")

    speech_segments = build_speech_segments(words, merge_gap=args.merge_gap)
    silence_gaps = build_silence_gaps(speech_segments)
    speech_share = speech_coverage_percent(
        speech_segments,
        media_duration_seconds=media_duration,
    )

    words_path = out_dir / "fortnite_words.json"
    speech_segments_path = out_dir / "fortnite_speech_segments.json"
    report_path = out_dir / "speech_1_report.txt"

    _write_json(words_path, words)
    _write_json(speech_segments_path, speech_segments)

    report_lines: list[str] = []
    report_lines.append("PROJECT ZENITH - SPEECH-1 REPORT")
    report_lines.append("")
    report_lines.append(f"video={video_path}")
    report_lines.append(f"model={args.model}")
    report_lines.append(f"merge_gap={args.merge_gap}")
    report_lines.append(f"media_duration_seconds={media_duration:.3f}")
    report_lines.append(f"samples={samples}")
    report_lines.append("")
    report_lines.append("TRACK PROBE")
    for row in probe_rows:
        report_lines.append(
            "- "
            + f"stream_index={row['stream_index']} "
            + f"audio_ordinal={row['audio_ordinal']} "
            + f"codec={row['codec']} "
            + f"channels={row['channels']} "
            + f"sample_rate={row['sample_rate']} "
            + f"words={row['word_count']} "
            + f"mean_confidence={_format_confidence(row['mean_confidence'])} "
            + f"selection_score={row['selection_score']:.4f}"
        )
        report_lines.append(f"  sample_text={row['sample_text'] or 'EMPTY'}")
        if row["errors"]:
            report_lines.append(f"  errors={row['errors']}")

    report_lines.append("")
    report_lines.append("SELECTED SPEECH TRACK")
    report_lines.append(
        f"stream_index={selected_row['stream_index']} audio_ordinal={selected_row['audio_ordinal']}"
    )
    report_lines.append(f"reason={selection_reason}")
    report_lines.append(
        "numbers="
        + f"words={selected_row['word_count']}, "
        + f"mean_confidence={_format_confidence(selected_row['mean_confidence'])}, "
        + f"selection_score={selected_row['selection_score']:.4f}"
    )
    report_lines.append("")
    report_lines.append("VALIDATION PHRASES")
    report_lines.extend(_phrase_lines(words, "Busfahrer"))
    report_lines.extend(_phrase_lines(words, "Was ist das fuer ein Cappuccino-Auto"))
    report_lines.append("")
    report_lines.append("STATISTICS")
    report_lines.append(f"word_count={len(words)}")
    report_lines.append(f"speech_segments={len(speech_segments)}")
    report_lines.append(f"silence_gaps={len(silence_gaps)}")
    report_lines.append(f"speech_share_percent={speech_share}")
    report_lines.append("")
    report_lines.append("OUTPUTS")
    report_lines.append(str(words_path))
    report_lines.append(str(speech_segments_path))
    report_lines.append(str(report_path))

    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print("\n".join(report_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
