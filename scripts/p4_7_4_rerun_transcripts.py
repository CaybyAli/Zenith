from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.learning_corpus_transcript import (
    build_faster_whisper_model,
    resolve_whisper_runtime_config,
)


@dataclass(frozen=True)
class TranscriptRepairResult:
    language: str
    segments_count: int
    first_10s_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "segments_count": self.segments_count,
            "first_10s_text": self.first_10s_text,
        }


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"fingerprint must be a JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temp_path = path.with_name(f"{path.stem}.tmp{path.suffix}")
    temp_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temp_path.replace(path)


def _source_video(folder: Path) -> Path | None:
    raw = folder / "raw.mp4"
    final = folder / "final.mp4"
    if raw.exists():
        return raw
    if final.exists():
        return final
    return None


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _segment_text(segment: Any) -> str:
    if isinstance(segment, dict):
        return _normalize_text(segment.get("text", ""))
    return _normalize_text(getattr(segment, "text", ""))


def _segment_start(segment: Any) -> float:
    if isinstance(segment, dict):
        raw = segment.get("start", 0.0)
    else:
        raw = getattr(segment, "start", 0.0)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _info_language(info: Any) -> str:
    if isinstance(info, dict):
        raw = info.get("language")
    else:
        raw = getattr(info, "language", None)
    clean = str(raw or "unknown").strip().lower()
    return clean or "unknown"


def _first_text(segments: Iterable[Any], *, first_seconds: float) -> tuple[int, str]:
    all_texts: list[str] = []
    first_window_texts: list[str] = []
    count = 0
    for segment in segments:
        count += 1
        text = _segment_text(segment)
        if not text:
            continue
        all_texts.append(text)
        if _segment_start(segment) < first_seconds:
            first_window_texts.append(text)

    first_text = _normalize_text(" ".join(first_window_texts))
    if len(first_text) < 10:
        first_text = _normalize_text(" ".join(all_texts[:6]))
    return count, first_text[:500]


def transcribe_source(
    transcriber: Any,
    source: Path,
    *,
    first_seconds: float,
    vad_filter: bool,
) -> TranscriptRepairResult:
    segments_iterable, info = transcriber.transcribe(
        str(source),
        language=None,
        vad_filter=vad_filter,
        word_timestamps=False,
    )
    segments_count, first_text = _first_text(
        segments_iterable,
        first_seconds=first_seconds,
    )
    return TranscriptRepairResult(
        language=_info_language(info),
        segments_count=segments_count,
        first_10s_text=first_text,
    )


def transcript_ok(payload: dict[str, Any]) -> bool:
    transcript = payload.get("transcript", {})
    return (
        str(transcript.get("language", "unknown")).strip().lower() != "unknown"
        and int(transcript.get("segments_count", 0)) > 5
        and len(str(transcript.get("first_10s_text", "")).strip()) >= 10
    )


def rerun_transcripts(
    *,
    corpus_root: Path,
    backup_dir: Path,
    model_name: str | None,
    device: str | None,
    compute_type: str | None,
    power_profile: str,
    first_seconds: float,
    vad_filter: bool,
    limit: int | None,
    missing_only: bool,
) -> dict[str, Any]:
    fingerprints = sorted(corpus_root.rglob("style_fingerprint.json"))
    if missing_only:
        fingerprints = [path for path in fingerprints if not transcript_ok(_read_json(path))]
    if limit is not None:
        fingerprints = fingerprints[:limit]

    backup_dir.mkdir(parents=True, exist_ok=True)
    config = resolve_whisper_runtime_config(
        power_profile=power_profile,
        model_name_or_path=model_name,
        device=device,
        compute_type=compute_type,
    )
    transcriber = build_faster_whisper_model(config)

    results: list[dict[str, Any]] = []
    for index, fingerprint_path in enumerate(fingerprints, start=1):
        folder = fingerprint_path.parent
        label = str(folder.relative_to(corpus_root))
        source = _source_video(folder)
        if source is None:
            results.append({"source": label, "status": "skip_no_video"})
            continue

        print(f"[P4.7-4] {index}/{len(fingerprints)} {label}")
        data = _read_json(fingerprint_path)
        backup_path = backup_dir / f"{label.replace('/', '_').replace(chr(92), '_')}_transcript_pre_p4_7_4.json"
        shutil.copy2(fingerprint_path, backup_path)
        try:
            transcript = transcribe_source(
                transcriber,
                source,
                first_seconds=first_seconds,
                vad_filter=vad_filter,
            ).to_dict()
            data["transcript"] = transcript
            data["p4_7_4_transcript_timestamp_utc"] = datetime.now(
                timezone.utc
            ).isoformat()
            data["p4_7_4_transcript_source"] = str(source)
            data["p4_7_4_transcript_model"] = {
                "model_name_or_path": config.model_name_or_path,
                "device": config.device,
                "compute_type": config.compute_type,
                "power_profile": config.power_profile,
                "vad_filter": vad_filter,
            }
            _write_json(fingerprint_path, data)
            results.append(
                {
                    "source": label,
                    "status": "ok",
                    "language": transcript["language"],
                    "segments_count": transcript["segments_count"],
                    "first_10s_text": transcript["first_10s_text"][:80],
                }
            )
        except Exception as exc:
            results.append({"source": label, "status": "error", "error": str(exc)})

    return audit(corpus_root=corpus_root, results=results)


def audit(*, corpus_root: Path, results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    ok_count = 0
    for fingerprint_path in sorted(corpus_root.rglob("style_fingerprint.json")):
        data = _read_json(fingerprint_path)
        rel = str(fingerprint_path.parent.relative_to(corpus_root))
        transcript = data.get("transcript", {})
        ok = transcript_ok(data)
        if ok:
            ok_count += 1
        entries.append(
            {
                "source": rel,
                "ok": ok,
                "language": transcript.get("language", "unknown"),
                "segments_count": transcript.get("segments_count", 0),
                "first_10s_length": len(str(transcript.get("first_10s_text", "") or "")),
            }
        )
    return {
        "entry_count": len(entries),
        "transcript_ok_count": ok_count,
        "problem_count": len(entries) - ok_count,
        "problems": [entry for entry in entries if not entry["ok"]],
        "entries": entries,
        "run_results": list(results or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", default="learning_corpus")
    parser.add_argument("--backup-dir", default="reports/phase4_7/p4_7_4_backup")
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--compute-type", default=None)
    parser.add_argument("--power-profile", default="performance")
    parser.add_argument("--first-seconds", type=float, default=10.0)
    parser.add_argument("--vad-filter", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--missing-only", action="store_true")
    parser.add_argument(
        "--report",
        default="reports/phase4_7/p4_7_4_transcript_audit.json",
    )
    args = parser.parse_args()

    report = rerun_transcripts(
        corpus_root=Path(args.corpus_root),
        backup_dir=Path(args.backup_dir),
        model_name=args.model_name,
        device=args.device,
        compute_type=args.compute_type,
        power_profile=args.power_profile,
        first_seconds=args.first_seconds,
        vad_filter=args.vad_filter,
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
    return 0 if report["transcript_ok_count"] >= 35 else 1


if __name__ == "__main__":
    raise SystemExit(main())
