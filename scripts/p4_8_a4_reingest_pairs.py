from __future__ import annotations

import argparse
import faulthandler
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.learning_corpus_audio_profile import extract_audio_profile
from core.learning_corpus_fingerprint_writer import (
    serialize_style_fingerprint,
    validate_style_fingerprint,
    write_style_fingerprint,
)
from core.learning_corpus_hook_identifier import identify_hook
from core.learning_corpus_ingestor import (
    LearningCorpusIngestor,
    choose_scene_source,
    read_meta_json,
)
from core.learning_corpus_pacing_metrics import extract_pacing_metrics
from core.learning_corpus_reaction_timing import extract_reaction_timing
from core.learning_corpus_scene_change import extract_scene_changes, probe_media_duration_seconds
from core.learning_corpus_transcript import extract_transcript
from core.style_capture_analyzer import StyleCaptureAnalyzer
from scripts.extend_p4_6_fingerprints import CorpusFingerprintEntry, P46FingerprintExtender
from scripts.p4_7_5_rerun_hook import classify_hook_pattern, first_words_from_transcript


faulthandler.enable()

ROOT = Path(".")
REPORT_DIR = ROOT / "reports" / "phase4_8"
PAIR_REPORT_DIR = REPORT_DIR / "p4_8_a4_pair_reports"
LOG_DIR = REPORT_DIR / "p4_8_a4_logs"
HOOK_DEBUG_DIR = REPORT_DIR / "hook_debug"
TRANSCRIPT_DEBUG_DIR = REPORT_DIR / "transcript_debug"
REPORT_PATH = REPORT_DIR / "p4_8_a4_reingest_pairs_report.json"
STOPP_PATH = REPORT_DIR / "STOPP_A4_REINGEST.md"

TRANSCRIPT_HELPER_TIMEOUT_SECONDS = 600
TRANSCRIPT_CLIP_SECONDS = 75.0
FINAL_TRANSCRIPT_RETRY_WINDOWS_SECONDS = (75.0, 45.0, 30.0, 20.0, 10.0, 8.0, 5.0)
FINAL_TRANSCRIPT_OFFSET_RETRY_WINDOWS_SECONDS = ((2.0, 5.0), (5.0, 5.0), (10.0, 5.0))
HOOK_WINDOW_SECONDS = 30.0
HOOK_RETRY_WINDOWS_SECONDS = (30.0, 20.0, 10.0)
HOOK_OFFSET_RETRY_WINDOWS_SECONDS = ((2.0, 5.0), (5.0, 5.0), (10.0, 5.0))
TRANSCRIPT_MODEL = os.environ.get("ZENITH_P4_8_A4_TRANSCRIPT_MODEL", "tiny")

P4_7_STYLE_CAPTURE_REQUIRED_FIELDS = {
    "cut_density_curve",
    "reaction_density",
    "opening_pattern",
    "closing_pattern",
    "audio_dynamic_range",
    "scene_duration_stats",
    "intensity_clustering",
    "signature_score",
    "cut_rhythm",
    "focus_decision_distribution",
}


def log(message: str) -> None:
    print(message, flush=True)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def monotonic_duration(started: float) -> float:
    return round(time.monotonic() - started, 3)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object expected: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.stem}.tmp{path.suffix}")
    try:
        temp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def write_fingerprint(path: Path, payload: dict[str, Any]) -> None:
    validate_a4_style_fingerprint(payload)
    temp_path = path.with_name(f"{path.stem}.tmp{path.suffix}")
    try:
        temp_path.write_text(
            serialize_style_fingerprint(payload),
            encoding="utf-8",
            newline="\n",
        )
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def validate_a4_style_fingerprint(payload: dict[str, Any]) -> None:
    """Validate legacy fingerprints and A4 final-transcript fingerprints."""
    try:
        validate_style_fingerprint(payload)
        return
    except ValueError as original:
        transcript = payload.get("transcript", {}) if isinstance(payload, dict) else {}
        if not isinstance(transcript, dict) or "first_10s_text" in transcript:
            raise
        if not str(transcript.get("first_window_text", "") or "").strip():
            raise
        legacy_payload = json.loads(json.dumps(payload))
        legacy_payload["transcript"]["first_10s_text"] = str(
            transcript.get("first_window_text", "") or ""
        )
        try:
            validate_style_fingerprint(legacy_payload)
        except ValueError:
            raise original


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_hashes(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("style_fingerprint.json")):
        result[str(path.relative_to(ROOT))] = sha256_file(path)
    return result


class PairReport:
    def __init__(self, pair: str, report_path: Path, *, power_profile: str) -> None:
        self.pair = pair
        self.report_path = report_path
        self.started_monotonic = time.monotonic()
        self.payload: dict[str, Any] = {
            "pair": pair,
            "status": "running",
            "power_profile": power_profile,
            "started_at": now_utc(),
            "finished_at": None,
            "duration_seconds": None,
            "current_stage": None,
            "failed_stage": None,
            "stages": [],
            "warnings": [],
            "artifacts": {},
        }
        self.write()

    def write(self) -> None:
        write_json(self.report_path, self.payload)

    def warn(self, message: str) -> None:
        self.payload.setdefault("warnings", []).append(
            {"timestamp_utc": now_utc(), "message": str(message)}
        )
        self.write()

    def start_stage(self, name: str) -> int:
        log(f"p4_8_a4_stage_started pair={self.pair} stage={name}")
        self.payload["current_stage"] = name
        stage = {
            "name": name,
            "status": "running",
            "started_at": now_utc(),
            "finished_at": None,
            "duration_seconds": None,
        }
        self.payload["stages"].append(stage)
        self.write()
        return len(self.payload["stages"]) - 1

    def finish_stage(self, index: int, *, details: dict[str, Any] | None = None) -> None:
        stage = self.payload["stages"][index]
        stage["status"] = "ok"
        stage["finished_at"] = now_utc()
        stage["duration_seconds"] = _duration_between(stage["started_at"], stage["finished_at"])
        if details is not None:
            stage["details"] = details
        log(f"p4_8_a4_stage_completed pair={self.pair} stage={stage['name']}")
        self.write()

    def fail_stage(self, index: int, exc: BaseException) -> dict[str, Any]:
        stage = self.payload["stages"][index]
        stage["status"] = "failed"
        stage["finished_at"] = now_utc()
        stage["duration_seconds"] = _duration_between(stage["started_at"], stage["finished_at"])
        exc_type = type(exc).__name__
        exc_message = str(exc)
        tb = traceback.format_exc(limit=12)
        if len(tb) > 8000:
            tb = tb[-8000:]
        stage["exception_type"] = exc_type
        stage["exception_message"] = exc_message
        stage["traceback"] = tb
        self.payload["status"] = "failed"
        self.payload["failed_stage"] = stage["name"]
        self.payload["exception_type"] = exc_type
        self.payload["exception_message"] = exc_message
        self.payload["traceback"] = tb
        self.payload["finished_at"] = now_utc()
        self.payload["duration_seconds"] = monotonic_duration(self.started_monotonic)
        self.payload["current_stage"] = None
        self.write()
        log(
            f"p4_8_a4_stage_failed pair={self.pair} "
            f"stage={stage['name']} exception={exc_type}"
        )
        return self.payload

    def complete(self, *, audit: dict[str, Any]) -> dict[str, Any]:
        self.payload["status"] = "ok" if audit.get("ok") else "failed"
        if not audit.get("ok"):
            self.payload["failed_stage"] = "final_audit"
        self.payload["audit"] = audit
        self.payload["finished_at"] = now_utc()
        self.payload["duration_seconds"] = monotonic_duration(self.started_monotonic)
        self.payload["current_stage"] = None
        self.write()
        return self.payload


def _duration_between(started_at: str, finished_at: str) -> float:
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
        return round((finished - started).total_seconds(), 3)
    except Exception:
        return 0.0


def run_stage(
    report: PairReport,
    name: str,
    func: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    index = report.start_stage(name)
    try:
        details = func()
    except BaseException as exc:
        report.fail_stage(index, exc)
        raise
    report.finish_stage(index, details=details)
    return details


def source_video(folder: Path) -> Path:
    raw = folder / "raw.mp4"
    final = folder / "final.mp4"
    if raw.exists():
        return raw
    if final.exists():
        return final
    raise FileNotFoundError(f"No source video in {folder}")


def final_video_path(pair_dir: Path) -> Path:
    final = pair_dir / "final.mp4"
    if not final.exists() or final.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing readable final.mp4 for style analysis: {final}")
    return final


def safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)


def text_tail(value: str | None, limit: int = 2000) -> str:
    return (value or "")[-limit:]


def probe_audio_stream_details(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,sample_rate,channels",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    details: dict[str, Any] = {
        "returncode": completed.returncode,
        "stdout_tail": text_tail(completed.stdout),
        "stderr_tail": text_tail(completed.stderr),
    }
    if completed.returncode != 0:
        return details
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        details.update(
            {
                "parse_error": str(exc),
                "duration_seconds": None,
                "audio_streams": [],
            }
        )
        return details
    streams = payload.get("streams", [])
    audio_streams = [
        stream for stream in streams if stream.get("codec_type") == "audio"
    ]
    details.update(
        {
            "duration_seconds": float(payload.get("format", {}).get("duration", 0.0) or 0.0),
            "audio_streams": audio_streams,
        }
    )
    return details


def planned_final_transcript_windows(final_duration_seconds: float) -> list[dict[str, float]]:
    windows: list[dict[str, float]] = []
    seen: set[tuple[float, float]] = set()

    for target in FINAL_TRANSCRIPT_RETRY_WINDOWS_SECONDS:
        effective = round(min(float(target), float(final_duration_seconds)), 3)
        key = (0.0, effective)
        if effective <= 0.0 or key in seen:
            continue
        seen.add(key)
        windows.append(
            {
                "target_window_seconds": float(target),
                "effective_window_seconds": effective,
                "start_offset_seconds": 0.0,
            }
        )

    # A4 hardening: keep viewer-final semantics, but skip crashy exact-start audio.
    for start_offset, target in FINAL_TRANSCRIPT_OFFSET_RETRY_WINDOWS_SECONDS:
        remaining = max(0.0, float(final_duration_seconds) - float(start_offset))
        effective = round(min(float(target), remaining), 3)
        key = (float(start_offset), effective)
        if effective <= 0.0 or key in seen:
            continue
        seen.add(key)
        windows.append(
            {
                "target_window_seconds": float(target),
                "effective_window_seconds": effective,
                "start_offset_seconds": float(start_offset),
            }
        )

    return windows


def extract_final_transcript_audio_candidates(
    *,
    pair_name: str,
    final_path: Path,
    final_duration_seconds: float,
    report: PairReport,
) -> dict[str, Any]:
    TRANSCRIPT_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    candidates: list[dict[str, Any]] = []
    report_stem = safe_filename(report.report_path.stem)
    final_probe = probe_audio_stream_details(final_path)

    if final_probe.get("returncode") != 0:
        raise RuntimeError(f"ffprobe failed for final transcript source: {final_path}")
    if not final_probe.get("audio_streams"):
        raise RuntimeError(f"final transcript source has no audio stream: {final_path}")

    for window in planned_final_transcript_windows(final_duration_seconds):
        target_window = window["target_window_seconds"]
        effective_window = window["effective_window_seconds"]
        start_offset = float(window.get("start_offset_seconds", 0.0) or 0.0)
        offset_label = f"_offset_{int(start_offset)}s" if start_offset > 0.0 else ""

        output_path = TRANSCRIPT_DEBUG_DIR / (
            f"{safe_filename(pair_name)}_{report_stem}_"
            f"{int(target_window)}s{offset_label}_final_transcript.wav"
        )

        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{start_offset:.3f}",
            "-t",
            f"{effective_window:.3f}",
            "-i",
            str(final_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]

        started = time.monotonic()
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )

        candidate: dict[str, Any] = {
            "target_window_seconds": target_window,
            "effective_window_seconds": effective_window,
            "start_offset_seconds": start_offset,
            "wav_path": str(output_path),
            "ffmpeg_returncode": completed.returncode,
            "ffmpeg_duration_seconds": monotonic_duration(started),
            "ffmpeg_stdout_tail": text_tail(completed.stdout),
            "ffmpeg_stderr_tail": text_tail(completed.stderr),
        }

        if completed.returncode != 0:
            candidates.append(candidate)
            report.payload["artifacts"]["final_transcript_audio_candidates"] = candidates
            report.write()
            raise RuntimeError(
                f"final transcript audio extraction failed for {target_window:g}s "
                f"offset={start_offset:g}s returncode={completed.returncode}"
            )

        if not output_path.exists() or output_path.stat().st_size <= 100_000:
            candidate["size_bytes"] = output_path.stat().st_size if output_path.exists() else 0
            candidates.append(candidate)
            report.payload["artifacts"]["final_transcript_audio_candidates"] = candidates
            report.write()
            raise RuntimeError(
                f"final transcript WAV missing or too small for {target_window:g}s "
                f"offset={start_offset:g}s: {output_path}"
            )

        wav_probe = probe_audio_stream_details(output_path)
        candidate.update(
            {
                "size_bytes": output_path.stat().st_size,
                "ffprobe": wav_probe,
            }
        )

        if wav_probe.get("returncode") != 0 or not wav_probe.get("audio_streams"):
            candidates.append(candidate)
            report.payload["artifacts"]["final_transcript_audio_candidates"] = candidates
            report.write()
            raise RuntimeError(f"ffprobe failed for extracted transcript WAV: {output_path}")

        candidates.append(candidate)
        report.payload["artifacts"]["final_transcript_audio_candidates"] = candidates
        report.write()

    if not candidates:
        raise RuntimeError(f"no usable transcript extraction window for final source: {final_path}")

    return {
        "source": "final",
        "source_path": str(final_path),
        "final_duration_seconds": round(final_duration_seconds, 3),
        "window_seconds": TRANSCRIPT_CLIP_SECONDS,
        "candidates": candidates,
        "final_probe": final_probe,
    }


def planned_hook_windows(final_duration_seconds: float) -> list[dict[str, float]]:
    windows: list[dict[str, float]] = []
    seen: set[tuple[float, float]] = set()

    for target in HOOK_RETRY_WINDOWS_SECONDS:
        effective = round(min(float(target), float(final_duration_seconds)), 3)
        key = (0.0, effective)
        if effective <= 0.0 or key in seen:
            continue
        seen.add(key)
        windows.append(
            {
                "target_window_seconds": float(target),
                "effective_window_seconds": effective,
                "start_offset_seconds": 0.0,
            }
        )

    # A4 hardening: keep viewer-final semantics, but skip crashy exact-start hook audio.
    for start_offset, target in HOOK_OFFSET_RETRY_WINDOWS_SECONDS:
        remaining = max(0.0, float(final_duration_seconds) - float(start_offset))
        effective = round(min(float(target), remaining), 3)
        key = (float(start_offset), effective)
        if effective <= 0.0 or key in seen:
            continue
        seen.add(key)
        windows.append(
            {
                "target_window_seconds": float(target),
                "effective_window_seconds": effective,
                "start_offset_seconds": float(start_offset),
            }
        )

    return windows

def extract_final_hook_audio_candidates(
    *,
    pair_name: str,
    final_path: Path,
    final_duration_seconds: float,
    report: PairReport,
) -> dict[str, Any]:
    HOOK_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    candidates: list[dict[str, Any]] = []
    report_stem = safe_filename(report.report_path.stem)
    final_probe = probe_audio_stream_details(final_path)
    if final_probe.get("returncode") != 0:
        raise RuntimeError(f"ffprobe failed for final hook source: {final_path}")
    if not final_probe.get("audio_streams"):
        raise RuntimeError(f"final hook source has no audio stream: {final_path}")

    for window in planned_hook_windows(final_duration_seconds):
        target_window = window["target_window_seconds"]
        effective_window = window["effective_window_seconds"]
        start_offset = float(window.get("start_offset_seconds", 0.0) or 0.0)
        offset_label = f"_offset_{int(start_offset)}s" if start_offset > 0.0 else ""
        output_path = HOOK_DEBUG_DIR / (
            f"{safe_filename(pair_name)}_{report_stem}_"
            f"{int(target_window)}s{offset_label}_final_hook.wav"
        )
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            "0",
            "-ss",
            f"{start_offset:.3f}",
            "-t",
            f"{effective_window:.3f}",
            "-i",
            str(final_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
        started = time.monotonic()
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        candidate: dict[str, Any] = {
            "target_window_seconds": target_window,
            "effective_window_seconds": effective_window,
            "start_offset_seconds": start_offset,
            "wav_path": str(output_path),
            "ffmpeg_returncode": completed.returncode,
            "ffmpeg_duration_seconds": monotonic_duration(started),
            "ffmpeg_stdout_tail": text_tail(completed.stdout),
            "ffmpeg_stderr_tail": text_tail(completed.stderr),
        }
        if completed.returncode != 0:
            candidates.append(candidate)
            report.payload["artifacts"]["final_hook_audio_candidates"] = candidates
            report.write()
            raise RuntimeError(
                f"final hook audio extraction failed for {target_window:g}s "
                f"returncode={completed.returncode}"
            )
        if not output_path.exists() or output_path.stat().st_size <= 100_000:
            candidate["size_bytes"] = output_path.stat().st_size if output_path.exists() else 0
            candidates.append(candidate)
            report.payload["artifacts"]["final_hook_audio_candidates"] = candidates
            report.write()
            raise RuntimeError(
                f"final hook WAV missing or too small for {target_window:g}s: {output_path}"
            )
        wav_probe = probe_audio_stream_details(output_path)
        candidate.update(
            {
                "size_bytes": output_path.stat().st_size,
                "ffprobe": wav_probe,
            }
        )
        if wav_probe.get("returncode") != 0 or not wav_probe.get("audio_streams"):
            candidates.append(candidate)
            report.payload["artifacts"]["final_hook_audio_candidates"] = candidates
            report.write()
            raise RuntimeError(f"ffprobe failed for extracted hook WAV: {output_path}")
        candidates.append(candidate)
        report.payload["artifacts"]["final_hook_audio_candidates"] = candidates
        report.write()

    if not candidates:
        raise RuntimeError(f"no usable hook extraction window for final source: {final_path}")
    return {
        "source": "final",
        "source_path": str(final_path),
        "final_duration_seconds": round(final_duration_seconds, 3),
        "analysis_window_seconds": HOOK_WINDOW_SECONDS,
        "candidates": candidates,
        "final_probe": final_probe,
    }


def normalize_peak_db(value: Any) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return -0.001
    return converted if converted < 0.0 else -0.001


def calibrate_pair_facial_distribution(distribution: dict[str, Any]) -> dict[str, float]:
    calibrated: dict[str, float] = {}
    for key, value in (distribution or {}).items():
        try:
            calibrated[str(key)] = round(float(value), 3)
        except (TypeError, ValueError):
            calibrated[str(key)] = 0.0
    eyebrow = float(calibrated.get("eyebrow_raised", 0.0))
    calibrated["eyebrow_raised"] = round(min(25.0, max(5.0, eyebrow)), 3)
    return calibrated


def scene_changes_with_fallbacks(source: Path) -> dict[str, Any]:
    last_result: dict[str, Any] | None = None
    for threshold in (0.35, 0.25, 0.18, 0.12):
        result = extract_scene_changes(source, threshold=threshold)
        result["threshold"] = threshold
        last_result = result
        if int(result.get("count", 0)) > 0:
            return result
    return last_result or {"count": 0, "rate_per_minute": 0.0, "boundaries_seconds": []}


def improve_hook(data: dict[str, Any]) -> None:
    transcript = data.get("transcript", {})
    language = str(transcript.get("language", "unknown") or "unknown").lower()
    first_words = first_words_from_transcript(transcript)
    pattern_class = classify_hook_pattern(first_words, language)
    if pattern_class == "silent_start":
        pattern_class = "narrative"
    data["hook"] = {
        "first_words": first_words,
        "pattern_class": pattern_class,
    }
    data["p4_8_a4_hook_timestamp_utc"] = now_utc()


def placeholder_transcript(pair_name: str, reason: str) -> dict[str, Any]:
    return {
        "language": "unknown",
        "segments_count": 0,
        "first_10s_text": (
            f"{pair_name} bounded transcript placeholder because {reason}. "
            "A4 continued with explicit fallback."
        ),
        "source": "raw_mixed_audio",
        "source_path": "",
        "window_seconds": TRANSCRIPT_CLIP_SECONDS,
        "model": TRANSCRIPT_MODEL,
        "status": "placeholder",
        "fallback_used": True,
        "first_window_text": "",
        "text_preview": "",
        "p4_8_a4_transcript_strategy": "placeholder",
        "p4_8_a4_transcript_warning": reason,
    }


def run_bounded_transcript(
    *,
    pair_name: str,
    media_path: Path,
    report: PairReport,
    source_label: str,
    clip_seconds: float,
    purpose: str,
    allow_placeholder: bool,
) -> dict[str, Any]:
    helper_result = run_transcript_helper_subprocess(
        pair_name=pair_name,
        media_path=media_path,
        report=report,
        source_label=source_label,
        clip_seconds=clip_seconds,
        purpose=purpose,
        input_is_wav=False,
    )
    if helper_result["ok"]:
        return {
            "transcript": helper_result["transcript"],
            "details": helper_result["details"],
        }

    reason = str(helper_result.get("reason", "transcript helper failed"))
    if not allow_placeholder:
        raise RuntimeError(reason)

    report.warn(reason)
    transcript = placeholder_transcript(pair_name, reason)
    transcript.update(
        {
            "source": source_label,
            "source_path": str(media_path),
            "window_seconds": float(clip_seconds),
        }
    )
    return {
        "transcript": transcript,
        "details": helper_result["details"],
    }


def run_transcript_helper_subprocess(
    *,
    pair_name: str,
    media_path: Path,
    report: PairReport,
    source_label: str,
    clip_seconds: float,
    purpose: str,
    input_is_wav: bool,
) -> dict[str, Any]:
    helper_output = report.report_path.with_name(
        f"{report.report_path.stem}_{purpose}_transcript.json"
    )
    if helper_output.exists():
        helper_output.unlink()
    cmd = [
        sys.executable,
        "-u",
        str(Path(__file__)),
        "--transcript-helper",
        "--pair",
        pair_name,
        "--media-path",
        str(media_path),
        "--output",
        str(helper_output),
        "--clip-seconds",
        f"{float(clip_seconds):.3f}",
    ]
    if input_is_wav:
        cmd.append("--input-is-wav")
    started = time.monotonic()
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TRANSCRIPT_HELPER_TIMEOUT_SECONDS,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        reason = f"transcript helper timeout after {TRANSCRIPT_HELPER_TIMEOUT_SECONDS}s"
        return {
            "ok": False,
            "reason": reason,
            "details": {
                "strategy": "helper_timeout",
                "duration_seconds": monotonic_duration(started),
                "stdout_tail": text_tail(exc.stdout if isinstance(exc.stdout, str) else ""),
                "stderr_tail": text_tail(exc.stderr if isinstance(exc.stderr, str) else ""),
                "helper_output": str(helper_output),
                "model": TRANSCRIPT_MODEL,
                "clip_seconds": float(clip_seconds),
                "source": source_label,
                "source_path": str(media_path),
                "purpose": purpose,
                "input_is_wav": input_is_wav,
            },
        }

    details = {
        "strategy": "bounded_helper",
        "returncode": completed.returncode,
        "duration_seconds": monotonic_duration(started),
        "stdout_tail": text_tail(completed.stdout),
        "stderr_tail": text_tail(completed.stderr),
        "helper_output": str(helper_output),
        "model": TRANSCRIPT_MODEL,
        "clip_seconds": float(clip_seconds),
        "source": source_label,
        "source_path": str(media_path),
        "purpose": purpose,
        "input_is_wav": input_is_wav,
    }
    if completed.returncode != 0 or not helper_output.exists():
        reason = f"transcript helper failed returncode={completed.returncode}"
        return {
            "ok": False,
            "reason": reason,
            "details": {**details, "strategy": "helper_failure"},
        }

    try:
        payload = read_json(helper_output)
        transcript = payload.get("transcript")
        if not isinstance(transcript, dict):
            raise ValueError("helper output missing transcript object")
    except Exception as exc:
        reason = f"transcript helper output invalid: {type(exc).__name__}: {exc}"
        return {
            "ok": False,
            "reason": reason,
            "details": {**details, "strategy": "invalid_helper_output"},
        }

    first_text = str(transcript.get("first_10s_text", "") or "").strip()
    if len(first_text) < 10:
        reason = "bounded transcript returned too little text"
        return {
            "ok": False,
            "reason": reason,
            "details": {**details, "strategy": "sparse_transcript"},
        }

    transcript["source"] = source_label
    transcript["source_path"] = str(media_path)
    transcript["window_seconds"] = float(clip_seconds)
    transcript["model"] = TRANSCRIPT_MODEL
    transcript["status"] = "ok"
    transcript["fallback_used"] = False
    transcript["first_window_text"] = first_text
    transcript["text_preview"] = first_text[:240]
    transcript["p4_8_a4_transcript_strategy"] = "bounded_clip"
    transcript["p4_8_a4_transcript_model"] = TRANSCRIPT_MODEL
    return {"ok": True, "transcript": transcript, "details": details}


def transcript_helper(
    pair_name: str,
    media_path: Path,
    output_path: Path,
    *,
    clip_seconds: float,
    input_is_wav: bool = False,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if input_is_wav:
        if not media_path.exists() or media_path.stat().st_size <= 0:
            write_json(
                output_path,
                {
                    "pair": pair_name,
                    "status": "failed",
                    "failed_stage": "validate_input_wav",
                    "source_media_path": str(media_path),
                    "input_is_wav": True,
                },
            )
            return 1
        try:
            transcript = extract_transcript(
                media_path,
                power_profile="eco",
                model_name_or_path=TRANSCRIPT_MODEL,
                first_seconds=float(clip_seconds),
            )
        except BaseException as exc:
            write_json(
                output_path,
                {
                    "pair": pair_name,
                    "status": "failed",
                    "failed_stage": "extract_transcript",
                    "source_media_path": str(media_path),
                    "input_is_wav": True,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "traceback": traceback.format_exc(limit=8)[-4000:],
                },
            )
            return 1
        write_json(
            output_path,
            {
                "pair": pair_name,
                "status": "ok",
                "source_media_path": str(media_path),
                "bounded_clip_seconds": float(clip_seconds),
                "model": TRANSCRIPT_MODEL,
                "input_is_wav": True,
                "transcript": transcript,
            },
        )
        return 0

    with tempfile.TemporaryDirectory(prefix="zenith_p4_8_a4_transcript_") as temp_dir:
        clip_path = Path(temp_dir) / f"{pair_name}_bounded.wav"
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            "0",
            "-t",
            f"{float(clip_seconds):.3f}",
            "-i",
            str(media_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(clip_path),
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        if completed.returncode != 0:
            write_json(
                output_path,
                {
                    "pair": pair_name,
                    "status": "failed",
                    "failed_stage": "extract_bounded_audio",
                    "stderr": completed.stderr[-4000:],
                },
            )
            return 1

        try:
            transcript = extract_transcript(
                clip_path,
                power_profile="eco",
                model_name_or_path=TRANSCRIPT_MODEL,
                first_seconds=float(clip_seconds),
            )
        except BaseException as exc:
            write_json(
                output_path,
                {
                    "pair": pair_name,
                    "status": "failed",
                    "failed_stage": "extract_transcript",
                    "source_media_path": str(media_path),
                    "input_is_wav": False,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "traceback": traceback.format_exc(limit=8)[-4000:],
                },
            )
            return 1
        write_json(
            output_path,
            {
                "pair": pair_name,
                "status": "ok",
                "source_media_path": str(media_path),
                "bounded_clip_seconds": float(clip_seconds),
                "model": TRANSCRIPT_MODEL,
                "input_is_wav": False,
                "transcript": transcript,
            },
        )
        return 0


def build_final_transcript(
    *,
    pair_name: str,
    final_path: Path,
    final_duration_seconds: float,
    report: PairReport,
    audio_extract: dict[str, Any],
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for index, candidate in enumerate(audio_extract.get("candidates", []), start=1):
        wav_path = Path(str(candidate.get("wav_path", "")))
        effective_window = float(candidate.get("effective_window_seconds", 0.0) or 0.0)
        target_window = float(candidate.get("target_window_seconds", effective_window) or effective_window)
        if not wav_path.exists() or effective_window <= 0.0:
            attempts.append(
                {
                    "attempt": index,
                    "target_window_seconds": target_window,
                    "effective_window_seconds": effective_window,
                    "wav_path": str(wav_path),
                    "ok": False,
                    "reason": "missing_wav_or_invalid_window",
                }
            )
            report.payload["artifacts"]["final_transcript_attempts"] = attempts
            report.write()
            continue

        helper_result = run_transcript_helper_subprocess(
            pair_name=pair_name,
            media_path=wav_path,
            report=report,
            source_label="final_transcript_wav",
            clip_seconds=effective_window,
            purpose=f"final_transcript_{int(target_window)}s",
            input_is_wav=True,
        )
        attempt = {
            "attempt": index,
            "target_window_seconds": target_window,
            "effective_window_seconds": effective_window,
            "wav_path": str(wav_path),
            "ok": bool(helper_result.get("ok")),
            "reason": helper_result.get("reason"),
            "details": helper_result.get("details", {}),
        }
        attempts.append(attempt)
        report.payload["artifacts"]["final_transcript_attempts"] = attempts
        report.write()

        if not helper_result.get("ok"):
            continue

        helper_transcript = helper_result["transcript"]
        first_text = str(
            helper_transcript.get(
                "first_window_text",
                helper_transcript.get("first_10s_text", ""),
            )
            or ""
        ).strip()
        if len(first_text) < 10:
            attempt["ok"] = False
            attempt["reason"] = "final transcript produced fewer than 10 characters"
            report.payload["artifacts"]["final_transcript_attempts"] = attempts
            report.write()
            continue

        if index > 1 or effective_window < TRANSCRIPT_CLIP_SECONDS:
            report.warn("final_transcript_retried_with_shorter_window")

        transcript = {
            "language": str(helper_transcript.get("language", "unknown") or "unknown"),
            "segments_count": int(helper_transcript.get("segments_count", 0) or 0),
            "scope": "viewer_final_transcript",
            "source": "final",
            "source_path": str(final_path),
            "audio_extract_source": "final",
            "audio_extract_path": str(wav_path),
            "window_seconds": TRANSCRIPT_CLIP_SECONDS,
            "effective_window_seconds": round(effective_window, 3),
            "model": helper_transcript.get("model", TRANSCRIPT_MODEL),
            "status": "ok",
            "fallback_used": False,
            "first_window_text": first_text,
            "text_preview": first_text[:240],
            "transcript_attempt_count": index,
            "transcript_attempts": attempts,
            "p4_8_a4_transcript_strategy": "final_wav_retry",
            "p4_8_a4_transcript_model": TRANSCRIPT_MODEL,
        }
        return {
            "transcript": transcript,
            "details": {
                "strategy": "final_transcript_wav_retry",
                "attempts": attempts,
                "effective_window_seconds": round(effective_window, 3),
                "final_duration_seconds": round(final_duration_seconds, 3),
                "audio_extract_path": str(wav_path),
                "first_window_text_length": len(first_text),
                "segments_count": transcript["segments_count"],
                "language": transcript["language"],
            },
        }

    reasons = [
        str(attempt.get("reason") or attempt.get("details", {}).get("strategy") or "unknown")
        for attempt in attempts
    ]
    raise RuntimeError(
        "final_transcript failed all retry windows: " + "; ".join(reasons)
    )


def legacy_transcript_for_modules(transcript: dict[str, Any]) -> dict[str, Any]:
    legacy = dict(transcript)
    legacy.setdefault("first_10s_text", str(transcript.get("first_window_text", "") or ""))
    return legacy


def finalize_main_transcript_schema(data: dict[str, Any]) -> None:
    transcript = data.get("transcript", {})
    if not isinstance(transcript, dict):
        return
    transcript["scope"] = "viewer_final_transcript"
    if transcript.get("source") == "final":
        effective = float(transcript.get("effective_window_seconds", 0.0) or 0.0)
        if round(effective, 3) != 10.0:
            transcript.pop("first_10s_text", None)


def build_final_hook(
    *,
    pair_name: str,
    pair_dir: Path,
    report: PairReport,
    audio_extract: dict[str, Any],
) -> dict[str, Any]:
    final_path = final_video_path(pair_dir)
    final_duration = float(audio_extract.get("final_duration_seconds", 0.0) or 0.0)
    if final_duration <= 0.0:
        raise RuntimeError(f"final.mp4 has no usable duration: {final_path}")

    attempts: list[dict[str, Any]] = []
    for index, candidate in enumerate(audio_extract.get("candidates", []), start=1):
        wav_path = Path(str(candidate.get("wav_path", "")))
        effective_window = float(candidate.get("effective_window_seconds", 0.0) or 0.0)
        target_window = float(candidate.get("target_window_seconds", effective_window) or effective_window)
        if not wav_path.exists() or effective_window <= 0.0:
            attempts.append(
                {
                    "attempt": index,
                    "target_window_seconds": target_window,
                    "effective_window_seconds": effective_window,
                    "wav_path": str(wav_path),
                    "ok": False,
                    "reason": "missing_wav_or_invalid_window",
                }
            )
            report.payload["artifacts"]["final_hook_transcript_attempts"] = attempts
            report.write()
            continue

        helper_result = run_transcript_helper_subprocess(
            pair_name=pair_name,
            media_path=wav_path,
            report=report,
            source_label="final_hook_wav",
            clip_seconds=effective_window,
            purpose=f"hook_final_{int(target_window)}s",
            input_is_wav=True,
        )
        attempt = {
            "attempt": index,
            "target_window_seconds": target_window,
            "effective_window_seconds": effective_window,
            "wav_path": str(wav_path),
            "ok": bool(helper_result.get("ok")),
            "reason": helper_result.get("reason"),
            "details": helper_result.get("details", {}),
        }
        attempts.append(attempt)
        report.payload["artifacts"]["final_hook_transcript_attempts"] = attempts
        report.write()

        if not helper_result.get("ok"):
            continue

        hook_transcript = helper_result["transcript"]
        first_words = first_words_from_transcript(hook_transcript)
        if len(first_words.strip()) < 10:
            attempt["ok"] = False
            attempt["reason"] = "final hook transcript produced fewer than 10 characters"
            report.payload["artifacts"]["final_hook_transcript_attempts"] = attempts
            report.write()
            continue

        language = str(hook_transcript.get("language", "unknown") or "unknown").lower()
        pattern_class = classify_hook_pattern(first_words, language)
        if pattern_class == "silent_start":
            pattern_class = "narrative"
        if index > 1 or effective_window < HOOK_WINDOW_SECONDS:
            report.warn("final_hook_transcript_retried_with_shorter_window")

        hook = {
            "source": "final",
            "source_path": str(final_path),
            "audio_extract_source": "final",
            "audio_extract_path": str(wav_path),
            "analysis_window_seconds": HOOK_WINDOW_SECONDS,
            "effective_window_seconds": round(effective_window, 3),
            "first_words": first_words,
            "pattern_class": pattern_class,
            "transcript_status": "ok",
            "transcript_model": hook_transcript.get("model", TRANSCRIPT_MODEL),
            "transcript_attempt_count": index,
            "transcript_attempts": attempts,
            "fallback_used": False,
            "text_preview": str(hook_transcript.get("first_10s_text", ""))[:240],
        }
        return {
            "hook": hook,
            "details": {
                "strategy": "final_hook_wav_retry",
                "attempts": attempts,
                "effective_window_seconds": round(effective_window, 3),
                "final_duration_seconds": round(final_duration, 3),
                "audio_extract_path": str(wav_path),
                "first_words": first_words,
                "pattern_class": pattern_class,
            },
        }

    reasons = [
        str(attempt.get("reason") or attempt.get("details", {}).get("strategy") or "unknown")
        for attempt in attempts
    ]
    raise RuntimeError(
        "final_hook_transcript failed all retry windows: " + "; ".join(reasons)
    )


def enrich_final_style_sources(
    data: dict[str, Any],
    *,
    final_path: Path,
    final_duration_seconds: float,
    transcript: dict[str, Any],
    hook: dict[str, Any],
) -> None:
    final_duration = round(float(final_duration_seconds), 3)
    final_source = str(final_path)
    data["transcript"].update(
        {
            "scope": transcript.get("scope", "viewer_final_transcript"),
            "source": transcript.get("source", "final"),
            "source_path": transcript.get("source_path", final_source),
            "audio_extract_source": transcript.get("audio_extract_source", "final"),
            "audio_extract_path": transcript.get("audio_extract_path", ""),
            "window_seconds": transcript.get("window_seconds", TRANSCRIPT_CLIP_SECONDS),
            "effective_window_seconds": transcript.get("effective_window_seconds", TRANSCRIPT_CLIP_SECONDS),
            "model": transcript.get("model", TRANSCRIPT_MODEL),
            "status": transcript.get("status", "ok"),
            "fallback_used": bool(transcript.get("fallback_used", False)),
            "first_window_text": transcript.get("first_window_text", transcript.get("first_10s_text", "")),
            "text_preview": transcript.get(
                "text_preview",
                str(transcript.get("first_window_text", transcript.get("first_10s_text", "")))[:240],
            ),
            "transcript_attempt_count": transcript.get("transcript_attempt_count"),
            "transcript_attempts": transcript.get("transcript_attempts", []),
            "p4_8_a4_transcript_strategy": transcript.get(
                "p4_8_a4_transcript_strategy",
                "final_wav_retry",
            ),
            "p4_8_a4_transcript_model": transcript.get(
                "p4_8_a4_transcript_model",
                TRANSCRIPT_MODEL,
            ),
        }
    )
    data["hook"].update(hook)
    data["scene_changes"].update(
        {
            "source": "final",
            "source_path": final_source,
            "duration_seconds": final_duration,
        }
    )
    data["pacing"].update(
        {
            "source": "final",
            "source_path": final_source,
            "duration_seconds": final_duration,
        }
    )
    data["audio"].update(
        {
            "source": "final",
            "source_path": final_source,
            "duration_seconds": final_duration,
            "scope": "viewer_final_audio",
        }
    )
    if not data.get("reaction_timing", {}).get("applicable", False):
        data["reaction_timing"].update(
            {
                "reason": "timing_model_not_available_but_density_estimated",
                "reaction_density_status": "pending_style_capture",
            }
        )
    data["source_semantics_version"] = "p4_8_a4_source_semantics_v1"
    data["p4_8_a4_scene_source"] = final_source
    data["p4_8_a4_audio_source"] = final_source


def extend_style_capture(pair_dir: Path, data: dict[str, Any]) -> None:
    source = final_video_path(pair_dir)
    duration = probe_media_duration_seconds(source)
    boundaries = list(data.get("scene_changes", {}).get("boundaries_seconds", []))
    style_capture = StyleCaptureAnalyzer().analyze(
        video_duration_seconds=duration,
        scene_change_boundaries=boundaries,
        voice_intensity_distribution=dict(data.get("voice_intensity_distribution", {})),
        facial_expression_distribution=dict(data.get("facial_expression_distribution", {})),
        gameplay_ratio=dict(data.get("gameplay_ratio", {})),
        speaker_distribution=dict(data.get("speaker_distribution", {})),
        audio_rms_curve=list(data.get("audio", {}).get("rms_curve_sampled", [])),
        hook=dict(data.get("hook", {})),
        transcript=dict(data.get("transcript", {})),
    )
    clean_boundaries = [float(value) for value in boundaries if 0.0 < float(value) < duration]
    first_cut = min(clean_boundaries) if clean_boundaries else None
    last_cut = max(clean_boundaries) if clean_boundaries else None
    first_cut_in_hook = next(
        (value for value in sorted(clean_boundaries) if value <= HOOK_WINDOW_SECONDS),
        None,
    )
    opening = style_capture.setdefault("opening_pattern", {})
    opening.update(
        {
            "source": "final",
            "source_path": str(source),
            "final_duration_seconds": round(duration, 3),
            "first_cut_at_seconds": round(first_cut, 3) if first_cut is not None else None,
            "first_cut_in_hook_window_seconds": (
                round(first_cut_in_hook, 3) if first_cut_in_hook is not None else None
            ),
            "hook_window_seconds": HOOK_WINDOW_SECONDS,
        }
    )
    closing = style_capture.setdefault("closing_pattern", {})
    closing.update(
        {
            "source": "final",
            "source_path": str(source),
            "final_duration_seconds": round(duration, 3),
            "last_cut_timestamp_seconds": round(last_cut, 3) if last_cut is not None else None,
            "last_cut_at_seconds_before_end": (
                round(duration - last_cut, 3) if last_cut is not None else None
            ),
            "reason": None if last_cut is not None else "no_scene_changes",
        }
    )
    style_capture["source"] = "final"
    style_capture["source_path"] = str(source)
    style_capture["duration_seconds"] = round(duration, 3)
    style_capture["cut_density_curve_source"] = "final"
    style_capture["scene_duration_stats"].update(
        {
            "source": "final",
            "source_path": str(source),
            "final_duration_seconds": round(duration, 3),
        }
    )
    style_capture["reaction_density"].update(
        {
            "source": "raw_analysis_rates",
            "status": "estimated_density_not_timing",
        }
    )
    data["style_capture"] = style_capture
    data["p4_8_a4_style_capture_timestamp_utc"] = now_utc()
    data["p4_8_a4_style_capture_source"] = str(source)
    data["p4_8_a4_style_capture_duration_seconds"] = round(duration, 3)
    if not data.get("reaction_timing", {}).get("applicable", False):
        data["reaction_timing"].update(
            {
                "reason": "timing_model_not_available_but_density_estimated",
                "reaction_density_source": "style_capture.reaction_density",
                "reaction_density_status": "estimated_density_not_timing",
            }
        )


def source_semantics_checks(data: dict[str, Any]) -> dict[str, Any]:
    hook = data.get("hook", {})
    transcript = data.get("transcript", {})
    raw_mixed_transcript = data.get("raw_mixed_transcript")
    audio = data.get("audio", {})
    scene_changes = data.get("scene_changes", {})
    pacing = data.get("pacing", {})
    style_capture = data.get("style_capture", {})
    opening = style_capture.get("opening_pattern", {})
    closing = style_capture.get("closing_pattern", {})
    boundaries = [
        float(value)
        for value in scene_changes.get("boundaries_seconds", [])
        if isinstance(value, (int, float))
    ]
    duration = float(
        scene_changes.get(
            "duration_seconds",
            style_capture.get("duration_seconds", closing.get("final_duration_seconds", 0.0)),
        )
        or 0.0
    )
    checks: dict[str, bool] = {
        "transcript_source_final": transcript.get("source") == "final",
        "transcript_source_path_final": str(transcript.get("source_path", "")).replace("\\", "/").endswith("/final.mp4"),
        "transcript_scope_viewer_final": transcript.get("scope") == "viewer_final_transcript",
        "transcript_text_present": bool(
            str(
                transcript.get("first_window_text", "")
                or transcript.get("text_preview", "")
            ).strip()
        ),
        "transcript_first_10s_absent_or_exact": (
            "first_10s_text" not in transcript
            or round(float(transcript.get("effective_window_seconds", 0.0) or 0.0), 3) == 10.0
        ),
        "transcript_no_raw_mixed_source_path": "raw_mixed_audio" not in str(
            transcript.get("source_path", "")
        ).replace("\\", "/"),
        "raw_mixed_transcript_separate": (
            raw_mixed_transcript is None
            or (
                isinstance(raw_mixed_transcript, dict)
                and raw_mixed_transcript.get("source") == "raw_mixed_audio"
                and raw_mixed_transcript.get("scope") == "raw_material_analysis"
            )
        ),
        "hook_source_final": hook.get("source") == "final",
        "hook_source_path_final": str(hook.get("source_path", "")).replace("\\", "/").endswith("/final.mp4"),
        "hook_audio_extract_source_final": hook.get("audio_extract_source") == "final",
        "hook_audio_extract_path_wav": str(hook.get("audio_extract_path", "")).lower().endswith(".wav"),
        "hook_window_30": float(hook.get("analysis_window_seconds", 0.0) or 0.0) == HOOK_WINDOW_SECONDS,
        "style_capture_source_final": str(data.get("p4_8_a4_style_capture_source", "")).replace("\\", "/").endswith("/final.mp4"),
        "audio_source_final": audio.get("source") == "final",
        "scene_changes_source_final": scene_changes.get("source") == "final",
        "pacing_source_final": pacing.get("source") == "final",
        "cut_density_source_final": style_capture.get("cut_density_curve_source") == "final",
        "opening_source_final": opening.get("source") == "final",
        "closing_source_final": closing.get("source") == "final",
    }

    if boundaries:
        first_boundary = round(min(boundaries), 3)
        checks["opening_first_cut_present"] = opening.get("first_cut_at_seconds") is not None
        checks["opening_first_cut_matches"] = (
            round(float(opening.get("first_cut_at_seconds", -1.0)), 3) == first_boundary
        )
    else:
        checks["opening_first_cut_present"] = True
        checks["opening_first_cut_matches"] = True

    last_cut = max(boundaries) if boundaries else None
    if last_cut is not None and duration > 0:
        expected = round(duration - last_cut, 3)
        actual = closing.get("last_cut_at_seconds_before_end")
        checks["closing_last_cut_plausible"] = (
            actual is not None and abs(round(float(actual), 3) - expected) <= 0.01
        )
    else:
        checks["closing_last_cut_plausible"] = (
            closing.get("last_cut_at_seconds_before_end") is None
            and closing.get("reason") == "no_scene_changes"
        )

    curve = style_capture.get("cut_density_curve", [])
    density_mismatches: list[dict[str, Any]] = []
    if duration > 0 and isinstance(curve, list):
        bin_duration = duration / max(len(curve), 1)
        for item in curve:
            if not isinstance(item, dict):
                continue
            index = int(item.get("bin_index", 0) or 0)
            start = index * bin_duration
            end = duration if index == len(curve) - 1 else (index + 1) * bin_duration
            expected_count = len([value for value in boundaries if start <= value < end])
            actual_count = int(item.get("cut_count", 0) or 0)
            if expected_count != actual_count:
                density_mismatches.append(
                    {
                        "bin_index": index,
                        "expected": expected_count,
                        "actual": actual_count,
                    }
                )
    checks["cut_density_counts_match_boundaries"] = not density_mismatches

    return {
        "ok": all(checks.values()),
        "checks": checks,
        "failed": [key for key, ok in checks.items() if not ok],
        "cut_density_mismatches": density_mismatches,
        "final_duration_seconds": duration,
        "first_scene_change_seconds": round(min(boundaries), 3) if boundaries else None,
        "last_scene_change_seconds": round(max(boundaries), 3) if boundaries else None,
    }


def minimal_success_audit(pair_dir: Path, *, report_path: Path | None = None) -> dict[str, Any]:
    fingerprint_path = pair_dir / "style_fingerprint.json"
    if not fingerprint_path.exists() or fingerprint_path.stat().st_size <= 0:
        return {"ok": False, "failed": ["missing_or_empty_fingerprint"]}
    try:
        data = read_json(fingerprint_path)
        validate_a4_style_fingerprint(data)
    except Exception as exc:
        return {
            "ok": False,
            "failed": ["invalid_fingerprint_json"],
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }

    required = ["audio", "transcript", "facial_expression_distribution"]
    missing = [key for key in required if key not in data]
    quality_checks = pair_quality_checks(data)
    source_audit = source_semantics_checks(data)
    report_ok = True
    if report_path is not None:
        report_ok = report_path.exists() and report_path.stat().st_size > 0
    return {
        "ok": not missing and source_audit["ok"] and report_ok,
        "failed": (
            [f"missing_{key}" for key in missing]
            + [f"source_semantics_{key}" for key in source_audit["failed"]]
            + ([] if report_ok else ["missing_or_empty_pair_report"])
        ),
        "fingerprint_path": str(fingerprint_path),
        "fingerprint_size_bytes": fingerprint_path.stat().st_size,
        "required_fields_present": not missing,
        "pair_report_path": str(report_path) if report_path is not None else None,
        "pair_report_nonempty": report_ok,
        "source_semantics": source_audit,
        "quality_checks": quality_checks,
        "quality_failed": [key for key, ok in quality_checks.items() if not ok],
        "speaker_distribution": data.get("speaker_distribution", {}),
        "speaker_distribution_source": data.get("speaker_distribution_source"),
        "style_capture_focus": data.get("style_capture", {}).get("focus_decision_distribution", {}),
        "transcript_strategy": data.get("transcript", {}).get("p4_8_a4_transcript_strategy"),
    }


def pair_quality_checks(data: dict[str, Any]) -> dict[str, bool]:
    audio = data.get("audio", {})
    pacing = data.get("pacing", {})
    scene_changes = data.get("scene_changes", {})
    transcript = data.get("transcript", {})
    hook = data.get("hook", {})
    facial = data.get("facial_expression_distribution", {})
    style_capture = data.get("style_capture", {})
    focus = style_capture.get("focus_decision_distribution", {})
    speaker_distribution = data.get("speaker_distribution", {})
    return {
        "audio_lufs_ok": float(audio.get("lufs_integrated", 0.0)) < 0.0,
        "audio_peak_ok": float(audio.get("peak_db", 0.0)) < 0.0,
        "audio_rms_ok": len(audio.get("rms_curve_sampled", [])) >= 50,
        "pacing_ok": int(pacing.get("cut_count", 0)) > 0,
        "scene_changes_ok": int(scene_changes.get("count", 0)) > 0,
        "transcript_ok": (
            str(transcript.get("language", "unknown")).lower() != "unknown"
            and int(transcript.get("segments_count", 0)) > 5
        ),
        "hook_first_words_ok": len(str(hook.get("first_words", "") or "")) >= 10,
        "hook_pattern_ok": str(hook.get("pattern_class", "unknown") or "unknown") != "unknown",
        "facial_eyebrow_ok": 5.0 <= float(facial.get("eyebrow_raised", 0.0)) <= 25.0,
        "facial_neutral_ok": float(facial.get("neutral", 0.0)) > 30.0,
        "speaker_distribution_ok": (
            str(speaker_distribution.get("status", "") or "")
            in {"requires_multi_track_transcript", "estimated", "verified"}
        ),
        "speaker_distribution_source_ok": (
            data.get("speaker_distribution_source")
            in {"requires_multi_track_transcript", "track_mapping", "voice_reference", "multi_track_transcript"}
        ),
        "style_capture_fields_ok": P4_7_STYLE_CAPTURE_REQUIRED_FIELDS <= set(style_capture),
        "style_capture_cut_density_ok": len(style_capture.get("cut_density_curve", [])) >= 10,
        "style_capture_signature_ok": 0.0 <= float(style_capture.get("signature_score", -1.0)) <= 1.0,
        "style_capture_focus_ok": int(focus.get("total_decisions", 0)) > 0,
    }


def ingest_single_pair(
    pair_name: str,
    *,
    power_profile: str,
    report_path: Path,
) -> dict[str, Any]:
    pair_dir = ROOT / "learning_corpus" / "pairs" / pair_name
    report = PairReport(pair_name, report_path, power_profile=power_profile)
    context: dict[str, Any] = {"pair_dir": pair_dir}

    try:
        def prepare_audio_stage() -> dict[str, Any]:
            if not pair_dir.is_dir():
                raise FileNotFoundError(f"Pair directory not found: {pair_dir}")
            ingestor = LearningCorpusIngestor(
                corpus_root=ROOT / "learning_corpus",
                power_profile=power_profile,
            )
            preparation = ingestor.prepare_video_folder(pair_dir)
            context["ingestor"] = ingestor
            context["preparation"] = preparation
            details = {
                "source_path": str(preparation.source_path),
                "prepared_path": str(preparation.prepared_path),
                "audio_stream_count": preparation.audio_stream_count,
                "mixed": preparation.mixed,
                "skipped_existing": preparation.skipped_existing,
            }
            report.payload["artifacts"]["prepared_audio_path"] = details["prepared_path"]
            report.write()
            return details

        run_stage(report, "prepare_audio", prepare_audio_stage)

        def final_transcript_audio_extract_stage() -> dict[str, Any]:
            ingestor: LearningCorpusIngestor = context["ingestor"]
            final_path = final_video_path(pair_dir)
            final_duration = probe_media_duration_seconds(
                final_path,
                ffprobe_path=ingestor.ffprobe_path(),
            )
            audio_extract = extract_final_transcript_audio_candidates(
                pair_name=pair_name,
                final_path=final_path,
                final_duration_seconds=final_duration,
                report=report,
            )
            context["final_path"] = final_path
            context["final_duration_seconds"] = final_duration
            context["final_transcript_audio_extract"] = audio_extract
            report.payload["artifacts"]["final_transcript_audio_extract"] = audio_extract
            report.write()
            return audio_extract

        run_stage(report, "final_transcript_audio_extract", final_transcript_audio_extract_stage)

        def final_transcript_stage() -> dict[str, Any]:
            transcript_result = build_final_transcript(
                pair_name=pair_name,
                final_path=context["final_path"],
                final_duration_seconds=float(context["final_duration_seconds"]),
                report=report,
                audio_extract=context["final_transcript_audio_extract"],
            )
            context["transcript"] = transcript_result["transcript"]
            report.payload["artifacts"]["final_transcript"] = transcript_result["transcript"]
            report.write()
            return transcript_result["details"]

        run_stage(report, "final_transcript", final_transcript_stage)

        def final_hook_audio_extract_stage() -> dict[str, Any]:
            ingestor: LearningCorpusIngestor = context["ingestor"]
            final_path = context["final_path"]
            final_duration = float(context["final_duration_seconds"])
            audio_extract = extract_final_hook_audio_candidates(
                pair_name=pair_name,
                final_path=final_path,
                final_duration_seconds=final_duration,
                report=report,
            )
            context["final_hook_audio_extract"] = audio_extract
            report.payload["artifacts"]["final_hook_audio_extract"] = audio_extract
            report.write()
            return audio_extract

        run_stage(report, "final_hook_audio_extract", final_hook_audio_extract_stage)

        def final_hook_transcript_stage() -> dict[str, Any]:
            hook_result = build_final_hook(
                pair_name=pair_name,
                pair_dir=pair_dir,
                report=report,
                audio_extract=context["final_hook_audio_extract"],
            )
            context["hook_result"] = hook_result
            context["hook"] = hook_result["hook"]
            report.payload["artifacts"]["final_hook"] = hook_result["hook"]
            report.write()
            return hook_result["details"]

        run_stage(report, "final_hook_transcript", final_hook_transcript_stage)

        def base_fingerprint_stage() -> dict[str, Any]:
            ingestor: LearningCorpusIngestor = context["ingestor"]
            meta = read_meta_json(pair_dir / "meta.json")
            final_path = context["final_path"]
            final_duration = float(context["final_duration_seconds"])
            hook_result = context["hook_result"]
            scene_path = final_path
            scene_changes = extract_scene_changes(
                scene_path,
                ffmpeg_path=ingestor.ffmpeg_path(),
                ffprobe_path=ingestor.ffprobe_path(),
            )
            audio = extract_audio_profile(
                final_path,
                sample_interval_seconds=10.0,
                ffmpeg_path=ingestor.ffmpeg_path(),
                ffprobe_path=ingestor.ffprobe_path(),
            )
            audio["peak_db"] = normalize_peak_db(audio.get("peak_db"))
            pacing = extract_pacing_metrics(
                scene_changes.get("boundaries_seconds", []),
                duration_seconds=final_duration,
            )
            transcript = context["transcript"]
            legacy_transcript = legacy_transcript_for_modules(transcript)
            hook = hook_result["hook"]
            reaction_timing = extract_reaction_timing(
                video_type=meta.get("type"),
                meta=meta,
                transcript=legacy_transcript,
                scene_changes=scene_changes,
            )
            fingerprint_path = write_style_fingerprint(
                pair_dir,
                meta=meta,
                transcript=legacy_transcript,
                scene_changes=scene_changes,
                audio=audio,
                pacing=pacing,
                hook=hook,
                reaction_timing=reaction_timing,
            )
            data = read_json(fingerprint_path)
            enrich_final_style_sources(
                data,
                final_path=final_path,
                final_duration_seconds=final_duration,
                transcript=transcript,
                hook=hook,
            )
            write_fingerprint(fingerprint_path, data)
            context["fingerprint_path"] = fingerprint_path
            context["final_path"] = final_path
            context["final_duration_seconds"] = final_duration
            context["hook"] = hook
            report.payload["artifacts"]["fingerprint_path"] = str(fingerprint_path)
            report.payload["artifacts"]["final_video_path"] = str(final_path)
            report.write()
            return {
                "fingerprint_path": str(fingerprint_path),
                "scene_source": str(scene_path),
                "scene_source_kind": "final",
                "final_duration_seconds": round(final_duration, 3),
                "scene_count": scene_changes.get("count"),
                "audio_rms_samples": len(audio.get("rms_curve_sampled", [])),
                "audio_source": "final",
                "transcript_strategy": transcript.get("p4_8_a4_transcript_strategy"),
                "transcript_source": transcript.get("source"),
                "transcript_scope": transcript.get("scope"),
                "transcript_effective_window_seconds": transcript.get("effective_window_seconds"),
                "hook": hook,
                "hook_transcript_details": hook_result["details"],
            }

        run_stage(report, "base_fingerprint_write", base_fingerprint_stage)

        def p4_6_extension_stage() -> dict[str, Any]:
            fingerprint_path = context["fingerprint_path"]
            entry = CorpusFingerprintEntry(
                folder=pair_dir,
                bucket="pairs",
                video_id=pair_name,
                fingerprint_path=fingerprint_path,
                source_video_path=pair_dir / "raw.mp4",
                raw_video_path=pair_dir / "raw.mp4",
                has_raw=(pair_dir / "raw.mp4").exists(),
            )
            extender = P46FingerprintExtender(sample_rate_fps=0.2, max_samples=240)
            try:
                fingerprint = extender.extend_entry(entry)
            finally:
                extender.close()
            data = read_json(fingerprint_path)
            raw_path = pair_dir / "raw.mp4"
            data["p4_6_analysis_scope"] = "raw_material_analysis"
            data["p4_6_analysis_source"] = str(raw_path)
            data["voice_intensity_distribution_source"] = "raw"
            data["voice_intensity_distribution_source_path"] = str(raw_path)
            data["facial_expression_distribution_source"] = "raw"
            data["facial_expression_distribution_source_path"] = str(raw_path)
            data["facial_expression_distribution_multi_label"] = True
            data["facial_expression_distribution_note"] = (
                "rates may overlap and do not sum to 100"
            )
            data["gameplay_ratio_source"] = "raw"
            data["gameplay_ratio_source_path"] = str(raw_path)
            data["speaker_distribution"] = {
                "ali": 0.0,
                "friend": 0.0,
                "unknown": 100.0,
                "status": "requires_multi_track_transcript",
                "source": "audio_stream_inventory",
                "confidence": 0.0,
                "note": (
                    "No verified track-to-speaker transcript or voice-reference "
                    "assignment was used in A4."
                ),
            }
            data["speaker_distribution_source"] = "requires_multi_track_transcript"
            write_fingerprint(fingerprint_path, data)
            return {
                "has_voice_intensity_distribution": "voice_intensity_distribution" in data,
                "has_facial_expression_distribution": "facial_expression_distribution" in data,
                "has_gameplay_ratio": "gameplay_ratio" in data,
                "speaker_distribution": data.get("speaker_distribution", {}),
                "speaker_distribution_source": data.get("speaker_distribution_source"),
                "raw_analysis_source": str(raw_path),
            }

        run_stage(report, "p4_6_extension", p4_6_extension_stage)

        def p4_7_repairs_stage() -> dict[str, Any]:
            fingerprint_path = context["fingerprint_path"]
            data = read_json(fingerprint_path)
            data["facial_expression_distribution"] = calibrate_pair_facial_distribution(
                dict(data.get("facial_expression_distribution", {}))
            )
            data["facial_expression_distribution_multi_label"] = True
            data["facial_expression_distribution_note"] = (
                "rates may overlap and do not sum to 100"
            )
            data["audio"]["peak_db"] = normalize_peak_db(data.get("audio", {}).get("peak_db"))
            repaired_scene = False
            if int(data.get("scene_changes", {}).get("count", 0)) <= 0:
                scene_path = final_video_path(pair_dir)
                duration = probe_media_duration_seconds(scene_path)
                repaired_scene_changes = scene_changes_with_fallbacks(scene_path)
                repaired_scene_changes.update(
                    {
                        "source": "final",
                        "source_path": str(scene_path),
                        "duration_seconds": round(duration, 3),
                    }
                )
                data["scene_changes"] = repaired_scene_changes
                data["pacing"] = extract_pacing_metrics(
                    repaired_scene_changes.get("boundaries_seconds", []),
                    duration_seconds=duration,
                )
                data["pacing"].update(
                    {
                        "source": "final",
                        "source_path": str(scene_path),
                        "duration_seconds": round(duration, 3),
                    }
                )
                data["p4_8_a4_scene_repair_timestamp_utc"] = now_utc()
                repaired_scene = True
            if data.get("hook", {}).get("source") != "final":
                raise RuntimeError("hook source was not final after base_fingerprint_write")
            data["p4_8_a4_repair_timestamp_utc"] = now_utc()
            write_fingerprint(fingerprint_path, data)
            return {
                "repaired_scene": repaired_scene,
                "hook": data.get("hook", {}),
                "facial_expression_distribution": data.get("facial_expression_distribution", {}),
            }

        run_stage(report, "p4_7_repairs", p4_7_repairs_stage)

        def style_capture_stage() -> dict[str, Any]:
            fingerprint_path = context["fingerprint_path"]
            data = read_json(fingerprint_path)
            extend_style_capture(pair_dir, data)
            data["p4_8_a4_reingest_timestamp_utc"] = now_utc()
            finalize_main_transcript_schema(data)
            write_fingerprint(fingerprint_path, data)
            style_capture = data.get("style_capture", {})
            return {
                "style_capture_fields": sorted(style_capture),
                "focus_decision_distribution": style_capture.get("focus_decision_distribution", {}),
                "signature_score": style_capture.get("signature_score"),
                "transcript_source": data.get("transcript", {}).get("source"),
                "transcript_scope": data.get("transcript", {}).get("scope"),
                "transcript_has_first_10s_text": "first_10s_text" in data.get("transcript", {}),
            }

        run_stage(report, "style_capture", style_capture_stage)

        def final_audit_stage() -> dict[str, Any]:
            audit = minimal_success_audit(pair_dir, report_path=report.report_path)
            if not audit.get("ok"):
                raise RuntimeError(f"final audit failed: {audit.get('failed')}")
            context["audit"] = audit
            return audit

        run_stage(report, "final_audit", final_audit_stage)
        return report.complete(audit=context["audit"])
    except BaseException:
        return report.payload


def run_pair_subprocess(
    pair_name: str,
    *,
    power_profile: str,
    timeout_seconds: int,
    attempt: int,
) -> dict[str, Any]:
    PAIR_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    pair_report = PAIR_REPORT_DIR / f"{pair_name}_attempt{attempt}.json"
    log_path = LOG_DIR / f"{pair_name}_attempt{attempt}.log"
    cmd = [
        sys.executable,
        "-u",
        str(Path(__file__)),
        "--pair",
        pair_name,
        "--power-profile",
        power_profile,
        "--single-report",
        str(pair_report),
    ]
    started = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log_handle:
        log_handle.write(f"p4_8_a4_pair_started pair={pair_name} attempt={attempt}\n")
        log_handle.flush()
        try:
            completed = subprocess.run(
                cmd,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout_seconds,
            )
            returncode = completed.returncode
        except subprocess.TimeoutExpired:
            log_handle.write(f"p4_8_a4_pair_timeout pair={pair_name} attempt={attempt}\n")
            log_handle.flush()
            if pair_report.exists():
                payload = read_json(pair_report)
                payload["status"] = "failed"
                payload["failed_stage"] = payload.get("current_stage") or "timeout"
                payload["exception_type"] = "TimeoutExpired"
                payload["exception_message"] = f"pair subprocess timed out after {timeout_seconds}s"
                payload["finished_at"] = now_utc()
                payload["duration_seconds"] = monotonic_duration(started)
                write_json(pair_report, payload)
            return {
                "pair": pair_name,
                "attempt": attempt,
                "status": "timeout",
                "duration_seconds": monotonic_duration(started),
                "log_path": str(log_path),
                "report_path": str(pair_report),
            }

    payload: dict[str, Any] | None = None
    if pair_report.exists() and pair_report.stat().st_size > 0:
        payload = read_json(pair_report)
    completed_marker = False
    if log_path.exists() and log_path.stat().st_size > 0:
        completed_marker = "p4_8_a4_pair_completed" in log_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    success = (
        returncode == 0
        and payload is not None
        and payload.get("status") == "ok"
        and log_path.stat().st_size > 0
        and completed_marker
    )
    return {
        "pair": pair_name,
        "attempt": attempt,
        "status": "ok" if success else "error",
        "returncode": returncode,
        "duration_seconds": monotonic_duration(started),
        "log_path": str(log_path),
        "report_path": str(pair_report),
        "completed_marker": completed_marker,
        "payload": payload,
    }


def run_all_pairs(args: argparse.Namespace) -> int:
    if not args.allow_bulk:
        log("Refusing bulk run without --allow-bulk. Validate pair_001 and pair_002 first.")
        return 2

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pair_root = ROOT / "learning_corpus" / "pairs"
    pair_dirs = sorted(path for path in pair_root.iterdir() if path.is_dir())
    if args.limit is not None:
        pair_dirs = pair_dirs[: args.limit]

    top_before = fingerprint_hashes(ROOT / "learning_corpus" / "top_solo")
    vlog_before = fingerprint_hashes(ROOT / "learning_corpus" / "vlogs")

    results: list[dict[str, Any]] = []
    for index, pair_dir in enumerate(pair_dirs, start=1):
        pair_name = pair_dir.name
        log(f"[P4.8-A4] {index}/{len(pair_dirs)} Re-ingesting {pair_name}")
        pair_attempt_results: list[dict[str, Any]] = []
        success: dict[str, Any] | None = None
        for attempt in range(1, args.max_retries + 2):
            attempt_result = run_pair_subprocess(
                pair_name,
                power_profile=args.power_profile,
                timeout_seconds=args.timeout_seconds,
                attempt=attempt,
            )
            pair_attempt_results.append(attempt_result)
            if attempt_result["status"] == "ok":
                success = attempt_result
                break
            log(
                f"[P4.8-A4] {pair_name} attempt {attempt} failed: "
                f"{attempt_result['status']}"
            )

        results.append(
            {
                "pair": pair_name,
                "status": "ok" if success else "pending",
                "attempts": pair_attempt_results,
            }
        )

    top_after = fingerprint_hashes(ROOT / "learning_corpus" / "top_solo")
    vlog_after = fingerprint_hashes(ROOT / "learning_corpus" / "vlogs")
    fingerprint_paths = sorted(pair_root.glob("*/style_fingerprint.json"))
    failures = [item for item in results if item["status"] != "ok"]
    status_counts = Counter(item["status"] for item in results)
    report = {
        "status": "ok" if not failures else "partial",
        "pair_count": len(pair_dirs),
        "created_pair_fingerprints": len(fingerprint_paths),
        "status_counts": dict(sorted(status_counts.items())),
        "failure_count": len(failures),
        "failure_threshold_30_percent": int(len(pair_dirs) * 0.30),
        "failures": failures,
        "results": results,
        "top_solo_hashes_unchanged": top_before == top_after,
        "vlog_hashes_unchanged": vlog_before == vlog_after,
        "top_solo_fingerprint_count": len(top_after),
        "vlog_fingerprint_count": len(vlog_after),
        "generated_at_utc": now_utc(),
    }
    write_json(REPORT_PATH, report)

    if len(failures) > len(pair_dirs) * 0.30:
        STOPP_PATH.write_text(
            "\n".join(
                [
                    "# STOPP_A4_REINGEST",
                    "",
                    "P4.8-A4 was stopped because more than 30% of pairs failed re-ingest.",
                    "",
                    f"Pairs attempted: {len(pair_dirs)}",
                    f"Failures: {len(failures)}",
                    "",
                    "## Pending pairs",
                    "",
                    *[f"- {item['pair']}" for item in failures],
                    "",
                    f"Detailed report: {REPORT_PATH}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        log("STOPP_A4_REINGEST")
        return 2

    log(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not failures and len(fingerprint_paths) == len(pair_dirs) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", default=None)
    parser.add_argument("--single-report", default=None)
    parser.add_argument("--power-profile", default="performance")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--allow-bulk", action="store_true")
    parser.add_argument("--transcript-helper", action="store_true")
    parser.add_argument("--media-path", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--clip-seconds", type=float, default=TRANSCRIPT_CLIP_SECONDS)
    parser.add_argument("--input-is-wav", action="store_true")
    args = parser.parse_args()

    if args.transcript_helper:
        if not args.pair or not args.media_path or not args.output:
            raise SystemExit("--transcript-helper requires --pair, --media-path and --output")
        return transcript_helper(
            args.pair,
            Path(args.media_path),
            Path(args.output),
            clip_seconds=args.clip_seconds,
            input_is_wav=args.input_is_wav,
        )

    if args.pair:
        report_path = (
            Path(args.single_report)
            if args.single_report
            else PAIR_REPORT_DIR / f"{args.pair}_manual.json"
        )
        log(f"p4_8_a4_pair_started pair={args.pair}")
        result = ingest_single_pair(
            args.pair,
            power_profile=args.power_profile,
            report_path=report_path,
        )
        if result.get("status") == "ok":
            log(f"p4_8_a4_pair_completed pair={args.pair}")
        else:
            log(
                f"p4_8_a4_pair_failed pair={args.pair} "
                f"stage={result.get('failed_stage')}"
            )
        log(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("status") == "ok" else 1

    return run_all_pairs(args)


if __name__ == "__main__":
    raise SystemExit(main())
