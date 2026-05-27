from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.audio_stream_inspector import AudioStreamInspector
from core.face_detector_mediapipe import MediaPipeFaceDetector
from core.facial_expression_analyzer import FacialExpressionAnalyzer
from core.gameplay_menu_detector import GameplayMenuDetector
from core.learning_corpus_fingerprint_writer import (
    current_ingest_timestamp_utc,
    serialize_style_fingerprint,
    validate_style_fingerprint,
)
from core.voice_intensity_analyzer import VoiceIntensityAnalyzer


@dataclass(frozen=True)
class CorpusFingerprintEntry:
    folder: Path
    bucket: str
    video_id: str
    fingerprint_path: Path
    source_video_path: Path
    raw_video_path: Path | None
    has_raw: bool


def discover_entries(corpus_root: str | Path = "learning_corpus") -> list[CorpusFingerprintEntry]:
    root = Path(corpus_root)
    entries: list[CorpusFingerprintEntry] = []
    for bucket in ("pairs", "top_solo", "vlogs"):
        bucket_dir = root / bucket
        if not bucket_dir.exists():
            continue
        for folder in sorted(path for path in bucket_dir.iterdir() if path.is_dir()):
            fingerprint_path = folder / "style_fingerprint.json"
            final_path = folder / "final.mp4"
            raw_path = folder / "raw.mp4"
            if not fingerprint_path.exists():
                continue
            source_path = raw_path if bucket == "pairs" and raw_path.exists() else final_path
            if not source_path.exists():
                continue
            entries.append(
                CorpusFingerprintEntry(
                    folder=folder,
                    bucket=bucket,
                    video_id=folder.name,
                    fingerprint_path=fingerprint_path,
                    source_video_path=source_path,
                    raw_video_path=raw_path if raw_path.exists() else None,
                    has_raw=raw_path.exists(),
                )
            )
    return entries


class P46FingerprintExtender:
    def __init__(
        self,
        *,
        voice_analyzer: VoiceIntensityAnalyzer | None = None,
        face_detector: MediaPipeFaceDetector | None = None,
        expression_analyzer: FacialExpressionAnalyzer | None = None,
        gameplay_detector: GameplayMenuDetector | None = None,
        audio_stream_inspector: AudioStreamInspector | None = None,
        sample_rate_fps: float = 0.2,
        max_samples: int | None = None,
    ) -> None:
        self.voice_analyzer = voice_analyzer or VoiceIntensityAnalyzer()
        self.face_detector = face_detector or MediaPipeFaceDetector()
        self.expression_analyzer = expression_analyzer or FacialExpressionAnalyzer()
        self.gameplay_detector = gameplay_detector or GameplayMenuDetector()
        self.audio_stream_inspector = audio_stream_inspector or AudioStreamInspector()
        self.sample_rate_fps = float(sample_rate_fps)
        self.max_samples = max_samples

    def close(self) -> None:
        close = getattr(self.face_detector, "close", None)
        if callable(close):
            close()

    def build_extension(self, entry: CorpusFingerprintEntry) -> dict[str, Any]:
        video_path = str(entry.source_video_path)

        voice_points = self.voice_analyzer.analyze(video_path, speaker="ali")
        face_points = self.face_detector.detect_in_video(
            video_path,
            sample_rate_fps=self.sample_rate_fps,
            max_samples=self.max_samples,
        )
        expression_points = self.expression_analyzer.analyze_video(face_points)
        gameplay_points = self.gameplay_detector.detect(
            video_path,
            sample_rate_fps=self.sample_rate_fps,
            max_samples=self.max_samples,
        )

        extension: dict[str, Any] = {
            "p4_6_extension_version": "1",
            "p4_6_extension_timestamp_utc": current_ingest_timestamp_utc(),
            "p4_6_analysis_source": str(entry.source_video_path),
            "voice_intensity_distribution": self.voice_analyzer.distribution(
                voice_points
            ),
            "facial_expression_distribution": self.expression_analyzer.distribution(
                expression_points
            ),
            "gameplay_ratio": self._gameplay_ratio(gameplay_points),
        }

        if entry.bucket == "pairs":
            extension["speaker_distribution"] = self._speaker_distribution(entry)
            extension["speaker_distribution_source"] = (
                "single_track_unknown_fallback"
                if extension["speaker_distribution"].get("unknown", 0.0) >= 100.0
                else "multi_track_transcript_required"
            )

        return extension

    def extend_entry(self, entry: CorpusFingerprintEntry) -> dict[str, Any]:
        fingerprint = _read_json(entry.fingerprint_path)
        fingerprint.update(self.build_extension(entry))
        validate_style_fingerprint(fingerprint)
        _write_json(entry.fingerprint_path, fingerprint)
        return fingerprint

    def _gameplay_ratio(
        self,
        gameplay_points: list[Any],
    ) -> dict[str, Any]:
        distribution = self.gameplay_detector.distribution(gameplay_points)
        return {
            "gameplay_percent": distribution.get("gameplay", 0.0),
            "menu_percent": distribution.get("menu", 0.0),
            "sample_count": len(gameplay_points),
        }

    def _speaker_distribution(self, entry: CorpusFingerprintEntry) -> dict[str, float]:
        if not entry.raw_video_path:
            return {"ali": 0.0, "friend": 0.0, "unknown": 100.0}
        try:
            inventory = self.audio_stream_inspector.inspect(str(entry.raw_video_path))
        except Exception:
            return {"ali": 0.0, "friend": 0.0, "unknown": 100.0}
        if not inventory.is_multi_track:
            return {"ali": 0.0, "friend": 0.0, "unknown": 100.0}
        has_mic = 1 if inventory.has_mic_track else 0
        has_discord = 1 if inventory.has_discord_track else 0
        known = has_mic + has_discord
        if known <= 0:
            return {"ali": 0.0, "friend": 0.0, "unknown": 100.0}
        return {
            "ali": round((has_mic / known) * 100.0, 3),
            "friend": round((has_discord / known) * 100.0, 3),
            "unknown": 0.0,
        }


def extend_corpus(
    corpus_root: str | Path = "learning_corpus",
    *,
    sample_rate_fps: float = 0.2,
    max_samples: int | None = None,
    limit: int | None = None,
    missing_only: bool = False,
) -> dict[str, Any]:
    entries = discover_entries(corpus_root)
    if missing_only:
        entries = [entry for entry in entries if entry_needs_extension(entry)]
    if limit is not None:
        entries = entries[:limit]

    extender = P46FingerprintExtender(
        sample_rate_fps=sample_rate_fps,
        max_samples=max_samples,
    )
    results: list[dict[str, Any]] = []
    try:
        for index, entry in enumerate(entries, start=1):
            print(f"[P4.6-9] {index}/{len(entries)} {entry.bucket}/{entry.video_id}")
            try:
                fingerprint = extender.extend_entry(entry)
                results.append(
                    {
                        "video_id": entry.video_id,
                        "bucket": entry.bucket,
                        "status": "ok",
                        "has_speaker_distribution": "speaker_distribution" in fingerprint,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "video_id": entry.video_id,
                        "bucket": entry.bucket,
                        "status": "error",
                        "error": str(exc),
                    }
                )
    finally:
        extender.close()

    return audit_extensions(corpus_root, expected_count=len(entries), results=results)


def audit_extensions(
    corpus_root: str | Path = "learning_corpus",
    *,
    expected_count: int | None = None,
    results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    entries = discover_entries(corpus_root)
    problems: list[dict[str, str]] = []
    extended_count = 0
    pair_speaker_count = 0
    for entry in entries:
        fingerprint = _read_json(entry.fingerprint_path)
        required = [
            "voice_intensity_distribution",
            "facial_expression_distribution",
            "gameplay_ratio",
        ]
        missing = [key for key in required if key not in fingerprint]
        if entry.bucket == "pairs" and "speaker_distribution" not in fingerprint:
            missing.append("speaker_distribution")
        if entry.bucket != "pairs" and "speaker_distribution" in fingerprint:
            missing.append("unexpected_speaker_distribution")
        if missing:
            problems.append(
                {
                    "video_id": entry.video_id,
                    "bucket": entry.bucket,
                    "problem": ",".join(missing),
                }
            )
            continue
        extended_count += 1
        if entry.bucket == "pairs":
            pair_speaker_count += 1

    return {
        "entry_count": len(entries),
        "expected_count": expected_count if expected_count is not None else len(entries),
        "extended_count": extended_count,
        "pair_speaker_distribution_count": pair_speaker_count,
        "problem_count": len(problems),
        "problems": problems,
        "run_results": list(results or []),
    }


def entry_needs_extension(entry: CorpusFingerprintEntry) -> bool:
    fingerprint = _read_json(entry.fingerprint_path)
    required = [
        "voice_intensity_distribution",
        "facial_expression_distribution",
        "gameplay_ratio",
    ]
    if any(key not in fingerprint for key in required):
        return True
    if entry.bucket == "pairs" and "speaker_distribution" not in fingerprint:
        return True
    if entry.bucket != "pairs" and "speaker_distribution" in fingerprint:
        return True
    return False


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"fingerprint must be a JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    serialized = serialize_style_fingerprint(payload)
    temp_path = path.with_name(f"{path.stem}.tmp{path.suffix}")
    try:
        temp_path.write_text(serialized, encoding="utf-8", newline="\n")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", default="learning_corpus")
    parser.add_argument("--sample-rate-fps", type=float, default=0.2)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--missing-only", action="store_true")
    parser.add_argument(
        "--report",
        default="reports/phase4_6/p4_6_9/fingerprint_extension_audit.json",
    )
    args = parser.parse_args()

    report = extend_corpus(
        args.corpus_root,
        sample_rate_fps=args.sample_rate_fps,
        max_samples=args.max_samples,
        limit=args.limit,
        missing_only=args.missing_only,
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["problem_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
