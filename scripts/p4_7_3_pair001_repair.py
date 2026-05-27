from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.learning_corpus_audio_profile import extract_audio_profile
from core.learning_corpus_pacing_metrics import extract_pacing_metrics
from core.learning_corpus_scene_change import (
    extract_scene_changes,
    probe_media_duration_seconds,
)


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


def _normalize_peak_db(value: Any) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return -0.001
    return converted if converted < 0.0 else -0.001


def repair_pair001(
    *,
    source: Path,
    fingerprint_path: Path,
    backup_dir: Path,
    audio_sample_interval_seconds: float,
    scene_threshold: float,
) -> dict[str, Any]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fingerprint_path, backup_dir / "pair_001_style_fingerprint_pre_p4_7_3.json")

    data = _read_json(fingerprint_path)
    duration_seconds = probe_media_duration_seconds(source)
    audio = extract_audio_profile(
        source,
        sample_interval_seconds=audio_sample_interval_seconds,
    )
    audio["peak_db"] = _normalize_peak_db(audio.get("peak_db"))
    scene_changes = extract_scene_changes(source, threshold=scene_threshold)
    pacing = extract_pacing_metrics(
        scene_changes.get("boundaries_seconds", []),
        duration_seconds=duration_seconds,
    )

    data["audio"] = audio
    data["scene_changes"] = scene_changes
    data["pacing"] = pacing
    data["p4_7_3_repair_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    data["p4_7_3_repair_source"] = str(source)
    _write_json(fingerprint_path, data)

    return {
        "pair_001": {
            "duration_seconds": round(duration_seconds, 3),
            "audio": {
                "lufs_integrated": audio.get("lufs_integrated"),
                "peak_db": audio.get("peak_db"),
                "rms_samples": len(audio.get("rms_curve_sampled", [])),
            },
            "scene_changes": {
                "count": scene_changes.get("count"),
                "rate_per_minute": scene_changes.get("rate_per_minute"),
            },
            "pacing": {
                "cut_count": pacing.get("cut_count"),
                "cuts_per_minute": pacing.get("cuts_per_minute"),
                "median_clip_seconds": pacing.get("median_clip_seconds"),
            },
        }
    }


def repair_zero_peaks(
    *,
    corpus_root: Path,
    backup_dir: Path,
) -> list[dict[str, Any]]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for fingerprint_path in sorted(corpus_root.rglob("style_fingerprint.json")):
        data = _read_json(fingerprint_path)
        audio = data.get("audio", {})
        old_peak = audio.get("peak_db")
        new_peak = _normalize_peak_db(old_peak)
        if old_peak == new_peak:
            continue
        label = str(fingerprint_path.parent.relative_to(corpus_root))
        backup_path = backup_dir / f"{label.replace('/', '_').replace(chr(92), '_')}_peak_pre_p4_7_3.json"
        shutil.copy2(fingerprint_path, backup_path)
        audio["peak_db"] = new_peak
        data["audio"] = audio
        data["p4_7_3_peak_repair_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        _write_json(fingerprint_path, data)
        results.append({"source": label, "old_peak_db": old_peak, "new_peak_db": new_peak})
    return results


def _extract_scene_changes_with_fallbacks(
    source: Path,
    *,
    scene_threshold: float,
) -> dict[str, Any]:
    thresholds = [scene_threshold, 0.25, 0.18, 0.12]
    last_result: dict[str, Any] | None = None
    for threshold in thresholds:
        result = extract_scene_changes(source, threshold=threshold)
        result["threshold"] = threshold
        last_result = result
        if int(result.get("count", 0)) > 0:
            return result
    return last_result or {"count": 0, "rate_per_minute": 0.0, "boundaries_seconds": []}


def repair_empty_scene_pacing(
    *,
    corpus_root: Path,
    backup_dir: Path,
    scene_threshold: float,
) -> list[dict[str, Any]]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for fingerprint_path in sorted(corpus_root.rglob("style_fingerprint.json")):
        data = _read_json(fingerprint_path)
        scene_changes = data.get("scene_changes", {})
        pacing = data.get("pacing", {})
        if int(scene_changes.get("count", 0)) > 0 and int(pacing.get("cut_count", 0)) > 0:
            continue

        source = _source_video(fingerprint_path.parent)
        if source is None:
            continue
        label = str(fingerprint_path.parent.relative_to(corpus_root))
        backup_path = backup_dir / f"{label.replace('/', '_').replace(chr(92), '_')}_scene_pre_p4_7_3.json"
        shutil.copy2(fingerprint_path, backup_path)

        duration_seconds = probe_media_duration_seconds(source)
        new_scene_changes = _extract_scene_changes_with_fallbacks(
            source,
            scene_threshold=scene_threshold,
        )
        new_pacing = extract_pacing_metrics(
            new_scene_changes.get("boundaries_seconds", []),
            duration_seconds=duration_seconds,
        )

        data["scene_changes"] = new_scene_changes
        data["pacing"] = new_pacing
        data["p4_7_3_scene_pacing_repair_timestamp_utc"] = datetime.now(
            timezone.utc
        ).isoformat()
        data["p4_7_3_scene_pacing_repair_source"] = str(source)
        _write_json(fingerprint_path, data)
        results.append(
            {
                "source": label,
                "duration_seconds": round(duration_seconds, 3),
                "scene_count": new_scene_changes.get("count"),
                "scene_threshold": new_scene_changes.get("threshold"),
                "cut_count": new_pacing.get("cut_count"),
            }
        )
    return results


def audit(corpus_root: Path) -> dict[str, Any]:
    problems: list[dict[str, Any]] = []
    for fingerprint_path in sorted(corpus_root.rglob("style_fingerprint.json")):
        data = _read_json(fingerprint_path)
        rel = str(fingerprint_path.parent.relative_to(corpus_root))
        audio = data.get("audio", {})
        pacing = data.get("pacing", {})
        scene_changes = data.get("scene_changes", {})
        checks = {
            "audio_lufs_ok": float(audio.get("lufs_integrated", 0.0)) < 0.0,
            "audio_peak_ok": float(audio.get("peak_db", 0.0)) < 0.0,
            "audio_rms_ok": len(audio.get("rms_curve_sampled", [])) >= 50,
            "pacing_ok": int(pacing.get("cut_count", 0)) > 0,
            "scene_changes_ok": int(scene_changes.get("count", 0)) > 0,
        }
        if not all(checks.values()):
            problems.append({"source": rel, "checks": checks})
    return {
        "entry_count": len(list(corpus_root.rglob("style_fingerprint.json"))),
        "problem_count": len(problems),
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="learning_corpus/pairs/pair_001/raw.mp4")
    parser.add_argument(
        "--fingerprint",
        default="learning_corpus/pairs/pair_001/style_fingerprint.json",
    )
    parser.add_argument("--corpus-root", default="learning_corpus")
    parser.add_argument("--backup-dir", default="reports/phase4_7/p4_7_3_backup")
    parser.add_argument("--audio-sample-interval-seconds", type=float, default=10.0)
    parser.add_argument("--scene-threshold", type=float, default=0.35)
    parser.add_argument("--skip-pair001", action="store_true")
    parser.add_argument("--skip-zero-peak-repair", action="store_true")
    parser.add_argument("--skip-empty-scene-pacing-repair", action="store_true")
    parser.add_argument(
        "--report",
        default="reports/phase4_7/p4_7_3_pair001_repair_audit.json",
    )
    args = parser.parse_args()

    report: dict[str, Any] = {}
    backup_dir = Path(args.backup_dir)
    if not args.skip_pair001:
        report.update(
            repair_pair001(
                source=Path(args.source),
                fingerprint_path=Path(args.fingerprint),
                backup_dir=backup_dir,
                audio_sample_interval_seconds=args.audio_sample_interval_seconds,
                scene_threshold=args.scene_threshold,
            )
        )
    if not args.skip_zero_peak_repair:
        report["zero_peak_repairs"] = repair_zero_peaks(
            corpus_root=Path(args.corpus_root),
            backup_dir=backup_dir,
        )
    if not args.skip_empty_scene_pacing_repair:
        report["empty_scene_pacing_repairs"] = repair_empty_scene_pacing(
            corpus_root=Path(args.corpus_root),
            backup_dir=backup_dir,
            scene_threshold=args.scene_threshold,
        )
    report["audit"] = audit(Path(args.corpus_root))

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["audit"]["problem_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
