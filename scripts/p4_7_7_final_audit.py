from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_STYLE_CAPTURE_FIELDS = {
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


def _checks(data: dict[str, Any], rel: str) -> dict[str, bool]:
    audio = data.get("audio", {})
    pacing = data.get("pacing", {})
    scene_changes = data.get("scene_changes", {})
    transcript = data.get("transcript", {})
    hook = data.get("hook", {})
    facial = data.get("facial_expression_distribution", {})
    style_capture = data.get("style_capture", {})
    eyebrow = float(facial.get("eyebrow_raised", 0.0))
    is_pair = rel.startswith("pairs")
    focus = style_capture.get("focus_decision_distribution", {})
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
        "facial_eyebrow_ok": (not is_pair) or (5.0 <= eyebrow <= 25.0),
        "facial_neutral_ok": float(facial.get("neutral", 0.0)) > 30.0,
        "style_capture_fields_ok": REQUIRED_STYLE_CAPTURE_FIELDS <= set(style_capture),
        "style_capture_cut_density_ok": len(style_capture.get("cut_density_curve", [])) >= 10,
        "style_capture_signature_ok": 0.0 <= float(style_capture.get("signature_score", -1.0)) <= 1.0,
        "style_capture_focus_ok": int(focus.get("total_decisions", 0)) > 0,
    }


def audit(corpus_root: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    field_failures: Counter[str] = Counter()
    hook_patterns: Counter[str] = Counter()
    clusters: Counter[str] = Counter()
    for fingerprint_path in sorted(corpus_root.rglob("style_fingerprint.json")):
        data = _read_json(fingerprint_path)
        rel = str(fingerprint_path.parent.relative_to(corpus_root))
        checks = _checks(data, rel)
        failed = [key for key, ok in checks.items() if not ok]
        for key in failed:
            field_failures[key] += 1
        hook_patterns[str(data.get("hook", {}).get("pattern_class", "unknown"))] += 1
        clusters[str(data.get("style_capture", {}).get("intensity_clustering", "missing"))] += 1
        entries.append(
            {
                "source": rel,
                "ok": not failed,
                "failed": failed,
                "checks": checks,
            }
        )

    all_green = [entry["source"] for entry in entries if entry["ok"]]
    return {
        "entry_count": len(entries),
        "all_green_count": len(all_green),
        "all_green_percent": round((len(all_green) / max(len(entries), 1)) * 100.0, 3),
        "field_failures": dict(sorted(field_failures.items())),
        "hook_pattern_distribution": dict(sorted(hook_patterns.items())),
        "intensity_clustering_distribution": dict(sorted(clusters.items())),
        "all_green": all_green,
        "partial_or_broken": [entry for entry in entries if not entry["ok"]],
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", default="learning_corpus")
    parser.add_argument("--report", default="reports/phase4_7/p4_7_7_final_audit.json")
    args = parser.parse_args()

    report = audit(Path(args.corpus_root))
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["all_green_count"] == report["entry_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
