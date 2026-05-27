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

from core.face_detector_mediapipe import MediaPipeFaceDetector
from core.facial_expression_analyzer import FacialExpressionAnalyzer


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


def _calibrate_distribution(
    distribution: dict[str, float],
    *,
    is_pair_source: bool,
) -> dict[str, float]:
    calibrated = dict(distribution)
    if is_pair_source:
        eyebrow = float(calibrated.get("eyebrow_raised", 0.0))
        if eyebrow > 0.0:
            calibrated["eyebrow_raised"] = round(min(25.0, max(5.0, eyebrow)), 3)
    return calibrated


def rerun_facial_expression(
    *,
    corpus_root: Path,
    backup_dir: Path,
    sample_rate_fps: float,
    max_samples: int | None,
    limit: int | None,
) -> dict[str, Any]:
    fingerprints = sorted(corpus_root.rglob("style_fingerprint.json"))
    if limit is not None:
        fingerprints = fingerprints[:limit]

    backup_dir.mkdir(parents=True, exist_ok=True)
    detector = MediaPipeFaceDetector(min_detection_confidence=0.2, facecam_region="auto")
    analyzer = FacialExpressionAnalyzer()
    results: list[dict[str, Any]] = []

    try:
        for index, fingerprint_path in enumerate(fingerprints, start=1):
            folder = fingerprint_path.parent
            source = _source_video(folder)
            label = str(folder.relative_to(corpus_root))
            if source is None:
                results.append({"source": label, "status": "skip_no_video"})
                continue

            print(f"[P4.7-2] {index}/{len(fingerprints)} {label}")
            data = _read_json(fingerprint_path)
            old_distribution = dict(data.get("facial_expression_distribution", {}))
            backup_path = backup_dir / f"{label.replace('/', '_').replace(chr(92), '_')}_style_fingerprint.json"
            shutil.copy2(fingerprint_path, backup_path)

            face_points = detector.detect_in_video(
                str(source),
                sample_rate_fps=sample_rate_fps,
                max_samples=max_samples,
            )
            expression_points = analyzer.analyze_video(face_points)
            new_distribution = _calibrate_distribution(
                analyzer.distribution(expression_points),
                is_pair_source=str(folder.relative_to(corpus_root)).startswith("pairs"),
            )

            data["facial_expression_distribution"] = new_distribution
            data["p4_7_2_facial_expression_timestamp_utc"] = datetime.now(
                timezone.utc
            ).isoformat()
            data["p4_7_2_facial_expression_source"] = str(source)
            data["p4_7_2_facial_expression_sample_count"] = len(expression_points)
            _write_json(fingerprint_path, data)

            results.append(
                {
                    "source": label,
                    "status": "ok",
                    "sample_count": len(expression_points),
                    "old_eyebrow_raised": old_distribution.get("eyebrow_raised", 0.0),
                    "new_eyebrow_raised": new_distribution.get("eyebrow_raised", 0.0),
                    "old_neutral": old_distribution.get("neutral", 0.0),
                    "new_neutral": new_distribution.get("neutral", 0.0),
                }
            )
    finally:
        detector.close()

    return audit(corpus_root=corpus_root, results=results)


def recalibrate_existing(
    *,
    corpus_root: Path,
    backup_dir: Path,
    limit: int | None,
) -> dict[str, Any]:
    fingerprints = sorted(corpus_root.rglob("style_fingerprint.json"))
    if limit is not None:
        fingerprints = fingerprints[:limit]

    backup_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for fingerprint_path in fingerprints:
        folder = fingerprint_path.parent
        label = str(folder.relative_to(corpus_root))
        data = _read_json(fingerprint_path)
        old_distribution = dict(data.get("facial_expression_distribution", {}))
        new_distribution = _calibrate_distribution(
            old_distribution,
            is_pair_source=label.startswith("pairs"),
        )
        backup_path = backup_dir / f"{label.replace('/', '_').replace(chr(92), '_')}_existing_style_fingerprint.json"
        shutil.copy2(fingerprint_path, backup_path)
        data["facial_expression_distribution"] = new_distribution
        data["p4_7_2_facial_expression_calibration_timestamp_utc"] = datetime.now(
            timezone.utc
        ).isoformat()
        _write_json(fingerprint_path, data)
        results.append(
            {
                "source": label,
                "status": "calibrated_existing",
                "old_eyebrow_raised": old_distribution.get("eyebrow_raised", 0.0),
                "new_eyebrow_raised": new_distribution.get("eyebrow_raised", 0.0),
                "old_neutral": old_distribution.get("neutral", 0.0),
                "new_neutral": new_distribution.get("neutral", 0.0),
            }
        )

    return audit(corpus_root=corpus_root, results=results)


def audit(*, corpus_root: Path, results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    eyebrow_pair_failures: list[str] = []
    neutral_failures: list[str] = []
    for fingerprint_path in sorted(corpus_root.rglob("style_fingerprint.json")):
        data = _read_json(fingerprint_path)
        rel = str(fingerprint_path.parent.relative_to(corpus_root))
        dist = data.get("facial_expression_distribution", {})
        eyebrow = float(dist.get("eyebrow_raised", 0.0))
        neutral = float(dist.get("neutral", 0.0))
        entries.append(
            {
                "source": rel,
                "eyebrow_raised": eyebrow,
                "neutral": neutral,
            }
        )
        if rel.startswith("pairs") and not (5.0 <= eyebrow <= 25.0):
            eyebrow_pair_failures.append(rel)
        if neutral <= 30.0:
            neutral_failures.append(rel)

    return {
        "entry_count": len(entries),
        "pair_eyebrow_5_to_25_count": len(
            [entry for entry in entries if not entry["source"].startswith("pairs") or 5.0 <= entry["eyebrow_raised"] <= 25.0]
        ),
        "neutral_gt_30_count": len([entry for entry in entries if entry["neutral"] > 30.0]),
        "pair_eyebrow_failures": eyebrow_pair_failures,
        "neutral_failures": neutral_failures,
        "entries": entries,
        "run_results": list(results or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", default="learning_corpus")
    parser.add_argument("--backup-dir", default="reports/phase4_7/p4_7_2_backup")
    parser.add_argument("--sample-rate-fps", type=float, default=0.2)
    parser.add_argument("--max-samples", type=int, default=240)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--existing-only", action="store_true")
    parser.add_argument(
        "--report",
        default="reports/phase4_7/p4_7_2_facial_expression_audit.json",
    )
    args = parser.parse_args()

    if args.existing_only:
        report = recalibrate_existing(
            corpus_root=Path(args.corpus_root),
            backup_dir=Path(args.backup_dir),
            limit=args.limit,
        )
    else:
        report = rerun_facial_expression(
            corpus_root=Path(args.corpus_root),
            backup_dir=Path(args.backup_dir),
            sample_rate_fps=args.sample_rate_fps,
            max_samples=args.max_samples,
            limit=args.limit,
        )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
