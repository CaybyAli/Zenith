from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.active_play_engagement_classifier import ActivePlayEngagementClassifier
from core.play_segment_boundary_detector import PlaySegmentBoundaryDetector
from models.play_segment import PlaySegment, PlaySegmentDetectionResult, PlaySignalWindow
from scripts.g6_2_play_segment_probe import DEFAULT_VIDEOS


OUTPUT_DIR = ROOT / "reports" / "g7a_engagement"


def _overlap_seconds(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _span_overlaps(span: Dict[str, Any], start: float, end: float) -> bool:
    return _overlap_seconds(
        float(span["start_seconds"]),
        float(span["end_seconds"]),
        start,
        end,
    ) > 0.0


def _synthetic_window(start: float, end: float, *, frozen: bool) -> PlaySignalWindow:
    if frozen:
        motion = 0.0
        scene = 0.0
        stability = 1.0
        audio = 0.0
        peak = 0.0
        richness = 0.45
    else:
        motion = 0.78
        scene = 0.66
        stability = 0.34
        audio = 0.72
        peak = 0.91
        richness = 0.88

    return PlaySignalWindow(
        start_seconds=start,
        end_seconds=end,
        motion_score=motion,
        audio_activity=audio,
        audio_peak_score=peak,
        scene_change_score=scene,
        visual_stability=stability,
        edge_stability=1.0 if frozen else 0.34,
        color_stability=1.0 if frozen else 0.28,
        state="active_play",
        intensity="low" if frozen else "high",
        confidence=0.80,
        evidence={
            "active_score": 0.20 if frozen else 0.78,
            "idle_score": 0.90 if frozen else 0.15,
            "transition_score": 0.05 if frozen else 0.45,
            "visual_richness": richness,
        },
        warnings=[],
    )


def build_synthetic_frozen_result() -> PlaySegmentDetectionResult:
    windows: List[PlaySignalWindow] = []
    t = 0.0
    while t < 20.0:
        frozen = 6.0 <= t < 14.0
        windows.append(_synthetic_window(t, t + 2.0, frozen=frozen))
        t += 2.0

    segment = PlaySegment(
        start_seconds=0.0,
        end_seconds=20.0,
        state="active_play",
        intensity="high",
        confidence=0.90,
        evidence={"synthetic_active_play_frozen_fixture": True},
        source_signal_counts={"windows": len(windows), "active_votes": len(windows)},
        warnings=[],
    )

    return PlaySegmentDetectionResult(
        video_path="synthetic_g7a_active_play_frozen_fixture",
        video_duration_seconds=20.0,
        analyzed_duration_seconds=20.0,
        window_seconds=2.0,
        taxonomy=["intro_menu_lobby", "active_play", "transition_dead_time", "replay_break", "unknown"],
        intensity_values=["low", "medium", "high", "unknown"],
        raw_windows=windows,
        segments=[segment],
        review_candidates={},
        warnings=[],
    )


def _minecraft_owner_checks(result: Dict[str, Any]) -> Dict[str, Any]:
    spans = result["spans"]

    empty_start, empty_end = 932.0, 936.0
    high_start, high_end = 966.0, 968.0

    empty_hits = [
        span for span in spans
        if _span_overlaps(span, empty_start, empty_end)
    ]
    high_hits = [
        span for span in spans
        if _span_overlaps(span, high_start, high_end)
    ]

    return {
        "empty_low_signal_window_932_936": {
            "range_seconds": [empty_start, empty_end],
            "expected": "trimmable_low_engagement",
            "status": "PASS" if any(span["keep_recommendation"] == "trimmable_low_engagement" for span in empty_hits) else "FAIL",
            "overlapping_spans": empty_hits,
        },
        "high_signal_honesty_window_966_968": {
            "range_seconds": [high_start, high_end],
            "expected": "keep_active",
            "status": "PASS" if any(span["keep_recommendation"] == "keep_active" for span in high_hits) else "FAIL",
            "overlapping_spans": high_hits,
            "honesty_note": (
                "High-signal moving/loud material must not be faked as low_engagement by G7a. "
                "If it is private/off-content, G7b transcript layer must handle it."
            ),
        },
    }


def _write_report(payload: Dict[str, Any]) -> Path:
    report_path = OUTPUT_DIR / "g7a_engagement_report.md"
    lines: List[str] = []

    lines.append("# G7a Engagement + Frozen/OBS-Pause Report")
    lines.append("")
    lines.append("## Scope")
    lines.append("- Additive Analyse-Schicht.")
    lines.append("- Ersetzt keine G6-States.")
    lines.append("- Kein Render.")
    lines.append("- Kein Transcript. G7b bleibt fuer private/off-content speech.")
    lines.append("")

    lines.append("## Schwellen / Formel")
    lines.append("```json")
    lines.append(json.dumps(payload["thresholds"], indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    lines.append("## Synthetic Frozen Proof")
    lines.append("```json")
    lines.append(json.dumps(payload["synthetic_frozen_proof"], indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")

    lines.append("## Videos")
    for label, item in payload["videos"].items():
        lines.append(f"### {label}")
        lines.append(f"- video_path: `{item['video_path']}`")
        lines.append(f"- analyzed_duration_seconds: {item['analyzed_duration_seconds']}")
        lines.append(f"- spans: {len(item['spans'])}")
        lines.append("")
        lines.append("#### keep/trimmable/frozen Anteil")
        lines.append("```json")
        lines.append(json.dumps(item["ratios"], indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")
        lines.append("#### Top-Spans")
        lines.append("```json")
        lines.append(json.dumps(item["spans"][:12], indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

        if label == "minecraft":
            lines.append("#### Minecraft Owner-Dead-Time Checks")
            lines.append("```json")
            lines.append(json.dumps(item["minecraft_owner_checks"], indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")

    lines.append("## Gesamtstatus")
    check_statuses = [payload["synthetic_frozen_proof"]["status"]]
    mc = payload["videos"].get("minecraft", {}).get("minecraft_owner_checks", {})
    for check in mc.values():
        check_statuses.append(check["status"])
    failed = [status for status in check_statuses if status != "PASS"]
    lines.append(f"- checks_total: {len(check_statuses)}")
    lines.append(f"- checks_failed: {len(failed)}")
    lines.append(f"- status: {'PASS' if not failed else 'FAIL'}")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def run_all_defaults() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    detector = PlaySegmentBoundaryDetector(window_seconds=2.0, visual_sample_seconds=1.0)
    classifier = ActivePlayEngagementClassifier()

    synthetic_result = classifier.classify(build_synthetic_frozen_result())
    synthetic_spans = [span.to_dict() for span in synthetic_result.spans]
    frozen_hits = [
        span for span in synthetic_spans
        if span["keep_recommendation"] == "frozen_or_paused"
        and _span_overlaps(span, 6.0, 14.0)
    ]

    payload: Dict[str, Any] = {
        "status": "diagnosis_and_analysis_only_no_render_no_commit",
        "thresholds": classifier.thresholds,
        "synthetic_frozen_proof": {
            "status": "PASS" if frozen_hits else "FAIL",
            "expected": "frozen_or_paused from 6s to 14s",
            "thresholds": classifier.thresholds,
            "spans": synthetic_spans,
        },
        "videos": {},
    }

    labels = ["rocket_league", "fortnite", "league_of_legends", "minecraft"]

    for label in labels:
        spec = DEFAULT_VIDEOS[label]
        path = Path(spec["path"])
        print(f"[G7a] START label={label} path={path}")

        result = detector.detect(
            path,
            max_duration_seconds=spec.get("max_duration_seconds"),
            include_raw_windows=True,
        )
        engagement = classifier.classify(result)
        data = engagement.to_dict()

        if label == "minecraft":
            data["minecraft_owner_checks"] = _minecraft_owner_checks(data)

        payload["videos"][label] = data

        out_path = OUTPUT_DIR / f"{label}_g7a_engagement.json"
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        print(
            f"[G7a] DONE label={label} "
            f"spans={len(data['spans'])} "
            f"keep={data['ratios']['keep_active_seconds']}s "
            f"low={data['ratios']['trimmable_low_engagement_seconds']}s "
            f"frozen={data['ratios']['frozen_or_paused_seconds']}s"
        )

    full_json = OUTPUT_DIR / "g7a_engagement_all.json"
    full_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = _write_report(payload)
    print(f"[G7a] JSON {full_json}")
    print(f"[G7a] REPORT {report_path}")

    check_statuses = [payload["synthetic_frozen_proof"]["status"]]
    mc_checks = payload["videos"]["minecraft"]["minecraft_owner_checks"]
    check_statuses.extend(check["status"] for check in mc_checks.values())
    failed = [status for status in check_statuses if status != "PASS"]

    print(f"[G7a] STATUS {'PASS' if not failed else 'FAIL'} failed={len(failed)}")
    return 0 if not failed else 2


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-defaults", action="store_true")
    args = parser.parse_args(argv)

    if not args.all_defaults:
        parser.error("use --all-defaults")

    return run_all_defaults()


if __name__ == "__main__":
    raise SystemExit(main())
