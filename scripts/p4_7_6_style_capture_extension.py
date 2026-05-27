from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.ffmpeg_helper import get_ffprobe_path
from core.style_capture_analyzer import StyleCaptureAnalyzer


STYLE_CAPTURE_REQUIRED_FIELDS = {
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


def _probe_duration(source: Path) -> float:
    completed = subprocess.run(
        [
            get_ffprobe_path(),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        return max(float(completed.stdout.strip()), 0.001)
    except ValueError:
        return 0.001


def extend_style_capture(
    *,
    corpus_root: Path,
    backup_dir: Path,
    limit: int | None,
) -> dict[str, Any]:
    fingerprints = sorted(corpus_root.rglob("style_fingerprint.json"))
    if limit is not None:
        fingerprints = fingerprints[:limit]

    backup_dir.mkdir(parents=True, exist_ok=True)
    analyzer = StyleCaptureAnalyzer()
    results: list[dict[str, Any]] = []
    for fingerprint_path in fingerprints:
        folder = fingerprint_path.parent
        label = str(folder.relative_to(corpus_root))
        source = _source_video(folder)
        if source is None:
            results.append({"source": label, "status": "skip_no_video"})
            continue
        data = _read_json(fingerprint_path)
        backup_path = backup_dir / f"{label.replace('/', '_').replace(chr(92), '_')}_style_capture_pre_p4_7_6.json"
        shutil.copy2(fingerprint_path, backup_path)

        style_capture = analyzer.analyze(
            video_duration_seconds=_probe_duration(source),
            scene_change_boundaries=list(data.get("scene_changes", {}).get("boundaries_seconds", [])),
            voice_intensity_distribution=dict(data.get("voice_intensity_distribution", {})),
            facial_expression_distribution=dict(data.get("facial_expression_distribution", {})),
            gameplay_ratio=dict(data.get("gameplay_ratio", {})),
            speaker_distribution=dict(data.get("speaker_distribution", {})),
            audio_rms_curve=list(data.get("audio", {}).get("rms_curve_sampled", [])),
            hook=dict(data.get("hook", {})),
            transcript=dict(data.get("transcript", {})),
        )
        data["style_capture"] = style_capture
        data["p4_7_6_style_capture_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        data["p4_7_6_style_capture_source"] = str(source)
        _write_json(fingerprint_path, data)
        results.append(
            {
                "source": label,
                "status": "ok",
                "intensity_clustering": style_capture.get("intensity_clustering"),
                "signature_score": style_capture.get("signature_score"),
                "cut_density_bins": len(style_capture.get("cut_density_curve", [])),
            }
        )

    return audit(corpus_root=corpus_root, results=results)


def audit(*, corpus_root: Path, results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    cluster_counts: Counter[str] = Counter()
    signature_scores: list[float] = []
    ok_count = 0
    for fingerprint_path in sorted(corpus_root.rglob("style_fingerprint.json")):
        data = _read_json(fingerprint_path)
        rel = str(fingerprint_path.parent.relative_to(corpus_root))
        style_capture = data.get("style_capture", {})
        missing = sorted(STYLE_CAPTURE_REQUIRED_FIELDS - set(style_capture))
        cut_density = style_capture.get("cut_density_curve", [])
        focus = style_capture.get("focus_decision_distribution", {})
        ok = (
            not missing
            and isinstance(cut_density, list)
            and len(cut_density) >= 10
            and 0.0 <= float(style_capture.get("signature_score", -1.0)) <= 1.0
            and int(focus.get("total_decisions", 0)) > 0
        )
        if ok:
            ok_count += 1
        cluster = str(style_capture.get("intensity_clustering", "missing"))
        cluster_counts[cluster] += 1
        try:
            signature_scores.append(float(style_capture.get("signature_score", 0.0)))
        except (TypeError, ValueError):
            signature_scores.append(0.0)
        entries.append(
            {
                "source": rel,
                "ok": ok,
                "missing": missing,
                "cut_density_bins": len(cut_density) if isinstance(cut_density, list) else 0,
                "intensity_clustering": cluster,
                "signature_score": style_capture.get("signature_score"),
            }
        )

    return {
        "entry_count": len(entries),
        "style_capture_ok_count": ok_count,
        "problem_count": len(entries) - ok_count,
        "distinct_intensity_clustering_count": len(cluster_counts),
        "intensity_clustering_distribution": dict(sorted(cluster_counts.items())),
        "signature_score_min": round(min(signature_scores), 3) if signature_scores else 0.0,
        "signature_score_max": round(max(signature_scores), 3) if signature_scores else 0.0,
        "signature_score_unique_count": len({round(score, 3) for score in signature_scores}),
        "problems": [entry for entry in entries if not entry["ok"]],
        "entries": entries,
        "run_results": list(results or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", default="learning_corpus")
    parser.add_argument("--backup-dir", default="reports/phase4_7/p4_7_6_backup")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--report",
        default="reports/phase4_7/p4_7_6_style_capture_audit.json",
    )
    args = parser.parse_args()

    report = extend_style_capture(
        corpus_root=Path(args.corpus_root),
        backup_dir=Path(args.backup_dir),
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
    return 0 if report["style_capture_ok_count"] == report["entry_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
