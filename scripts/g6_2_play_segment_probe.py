from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.play_segment_boundary_detector import FORBIDDEN_CORE_TERMS, PlaySegmentBoundaryDetector
from models.play_segment import active_vs_idle_menu_share, dominant_state, duration_by_state


OUTPUT_DIR = ROOT / "reports" / "g6_2_play_segment_detector"

DEFAULT_VIDEOS: Dict[str, Dict[str, Any]] = {
    "rocket_league": {
        "path": ROOT / "tests" / "Rocket League Neuer Test58.mp4",
        "max_duration_seconds": 30.0,
        "ground_truth": {
            "taxonomy_only": True,
        },
    },
    "fortnite": {
        "path": ROOT / "inbox" / "gaming_main" / "Fortnite Full Video.mp4",
        "max_duration_seconds": None,
        "ground_truth": {
            "active_start": 15.58,
            "not_active_ranges": [
                (0.0, 15.58, "pre_gameplay_head"),
                (255.37, 285.58, "not_active_04_15_37_to_04_45_58"),
                (599.14, 693.08, "not_active_09_59_14_to_11_33_08"),
                (1811.51, 1820.49, "not_active_30_11_51_to_30_20_49"),
            ],
        },
    },
    "league_of_legends": {
        "path": ROOT / "inbox" / "gaming_main" / "League of Legends Full Video Neu.mp4",
        "max_duration_seconds": None,
        "ground_truth": {
            "active_start": 178.0,
            "not_active_ranges": [
                (0.0, 178.0, "pre_gameplay_head"),
                (993.19, 1009.51, "not_active_16_33_19_to_16_49_51"),
            ],
            "post_start_dominant_active": {
                "start": 178.0,
                "exclude_ranges": [
                    {"start_seconds": 993.19, "end_seconds": 1009.51},
                ],
            },
        },
    },
    "minecraft": {
        "path": ROOT / "inbox" / "gaming_main" / "Minecraft Full Video.mp4",
        "max_duration_seconds": None,
        "ground_truth": {
            "active_start": 381.0,
            "not_active_ranges": [
                (0.0, 381.0, "pre_gameplay_head"),
                (195.31, 231.42, "not_active_03_15_31_to_03_51_42"),
                (915.39, 986.28, "not_active_15_15_39_to_16_26_28"),
                (2625.14, 2655.31, "not_active_43_45_14_to_44_15_31"),
            ],
        },
    },
}


def _range_totals(result: Any, start: float, end: float) -> Dict[str, float]:
    return duration_by_state(result.segments, start, min(end, result.analyzed_duration_seconds))


def _active_share(result: Any, start: float, end: float) -> float:
    totals = _range_totals(result, start, end)
    total = sum(totals.values())
    if total <= 0:
        return 0.0
    return totals.get("active_play", 0.0) / total


def _dominant(result: Any, start: float, end: float) -> str:
    return dominant_state(result.segments, start, min(end, result.analyzed_duration_seconds))


def _passfail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def _evaluate_ground_truth(label: str, result: Any, spec: Mapping[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    # Core taxonomy leak check for every run.
    emitted_states = sorted({segment.state for segment in result.segments})
    emitted_intensities = sorted({segment.intensity for segment in result.segments})
    haystack = " ".join(emitted_states + emitted_intensities).lower()
    leaked_terms = [term for term in FORBIDDEN_CORE_TERMS if term in haystack]
    checks.append(
        {
            "name": "neutral_taxonomy_no_forbidden_core_terms",
            "status": _passfail(not leaked_terms),
            "details": {
                "emitted_states": emitted_states,
                "emitted_intensities": emitted_intensities,
                "leaked_terms": leaked_terms,
            },
        }
    )

    gt = spec.get("ground_truth", {})
    if gt.get("taxonomy_only"):
        return {"checks": checks, "lol_active_vs_idle_menu_share": None}

    active_start = gt.get("active_start")
    if active_start is not None:
        active_start = float(active_start)
        probe_end = min(result.analyzed_duration_seconds, active_start + 90.0)
        dom = _dominant(result, active_start, probe_end)
        share = _active_share(result, active_start, probe_end)
        checks.append(
            {
                "name": "active_play_start_plausible",
                "status": _passfail(dom == "active_play" and share >= 0.50),
                "range": [round(active_start, 3), round(probe_end, 3)],
                "details": {
                    "dominant_state": dom,
                    "active_play_share": round(share, 4),
                    "state_seconds": _range_totals(result, active_start, probe_end),
                },
            }
        )

    for start, end, name in gt.get("not_active_ranges", []):
        start_f = float(start)
        end_f = float(end)
        dom = _dominant(result, start_f, end_f)
        share = _active_share(result, start_f, end_f)
        totals = _range_totals(result, start_f, end_f)
        total_seconds = sum(totals.values())
        non_active_share = 1.0 - share if total_seconds > 0 else 0.0
        checks.append(
            {
                "name": name,
                "status": _passfail(share < 0.50),
                "range": [round(start_f, 3), round(min(end_f, result.analyzed_duration_seconds), 3)],
                "details": {
                    "dominant_state": dom,
                    "active_play_share": round(share, 4),
                    "non_active_share": round(non_active_share, 4),
                    "state_seconds": totals,
                    "pass_rule": "active_play_share < 0.50",
                },
            }
        )

    lol_share = None
    if "post_start_dominant_active" in gt:
        post = gt["post_start_dominant_active"]
        start_f = float(post["start"])
        end_f = result.analyzed_duration_seconds
        lol_share = active_vs_idle_menu_share(
            result.segments,
            start_f,
            end_f,
            exclude_ranges=post.get("exclude_ranges", []),
        )
        checks.append(
            {
                "name": "lol_post_02_58_active_play_dominant_excluding_known_break",
                "status": _passfail(lol_share["active_play_share"] > lol_share["idle_menu_share"]),
                "range": [round(start_f, 3), round(end_f, 3)],
                "details": lol_share,
            }
        )

    return {"checks": checks, "lol_active_vs_idle_menu_share": lol_share}


def _segment_extract(result: Any, limit: int = 8) -> List[Dict[str, Any]]:
    return [segment.to_dict() for segment in result.segments[:limit]]


def _write_report(results: Dict[str, Any], evaluations: Dict[str, Any]) -> Path:
    report_path = OUTPUT_DIR / "g6_2_play_segment_detector_report.md"

    lines: List[str] = []
    lines.append("# G6 Stufe 2 Play Segment Boundary Detector Report")
    lines.append("")
    lines.append("## Scope")
    lines.append("- Eigenstaendige Analyse-Schicht.")
    lines.append("- Kein Render.")
    lines.append("- Kein Timeline/Render-Wiring.")
    lines.append("- Core taxonomy: intro_menu_lobby | active_play | transition_dead_time | replay_break | unknown.")
    lines.append("- Intensity ist separat: low | medium | high | unknown.")
    lines.append("")

    lines.append("## Multi-Signal Logik")
    lines.append("```text")
    lines.append("active_score = 0.28*motion + 0.25*audio_activity + 0.08*audio_peak + 0.12*visual_stability + 0.08*edge_stability + 0.07*color_stability + 0.12*visual_richness")
    lines.append("idle_score = 0.28*(1-motion) + 0.28*(1-audio_activity) + 0.22*visual_stability + 0.12*(1-visual_richness) + 0.10*(1-audio_peak)")
    lines.append("transition_score = 0.42*scene_change + 0.22*(1-audio_activity) + 0.18*(1-edge_stability) + 0.18*(1-color_stability)")
    lines.append("quiet_active_rule = motion <= 0.36 AND audio_activity >= 0.18 AND avg(visual_stability, edge_stability, color_stability) >= 0.44")
    lines.append("confidence = clamp01(0.48 + abs(active_score - max(idle_score, transition_score)))")
    lines.append("```")
    lines.append("")

    lines.append("## Dateien")
    lines.append("- models/play_segment.py")
    lines.append("- core/play_segment_boundary_detector.py")
    lines.append("- scratch/g6_2_play_segment_probe.py")
    lines.append("- reports/g6_2_play_segment_detector/<label>_g6_2_segments.json")
    lines.append("- reports/g6_2_play_segment_detector/g6_2_play_segment_detector_report.md")
    lines.append("")

    lines.append("## Ergebnis pro Video")
    for label, result in results.items():
        data = result.to_dict(include_raw_windows=False)
        evaluation = evaluations[label]
        json_path = OUTPUT_DIR / f"{label}_g6_2_segments.json"

        lines.append(f"### {label}")
        lines.append(f"- video_path: `{data['video_path']}`")
        lines.append(f"- video_duration_seconds: {data['video_duration_seconds']}")
        lines.append(f"- analyzed_duration_seconds: {data['analyzed_duration_seconds']}")
        lines.append(f"- segments: {len(data['segments'])}")
        lines.append(f"- json: `{json_path}`")
        lines.append("")

        lines.append("#### JSON-Auszug")
        lines.append("```json")
        lines.append(json.dumps(_segment_extract(result), indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

        lines.append("#### Review-Kandidaten")
        lines.append("```json")
        lines.append(json.dumps(data["review_candidates"], indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

        lines.append("#### Ground Truth Checks")
        for check in evaluation["checks"]:
            lines.append(f"- {check['status']} `{check['name']}`")
            if "range" in check:
                lines.append(f"  - range_seconds: {check['range']}")
            lines.append(f"  - details: `{json.dumps(check['details'], ensure_ascii=False)}`")
        lines.append("")

        if evaluation.get("lol_active_vs_idle_menu_share"):
            lines.append("#### LoL active_play vs idle/menu Anteil")
            lines.append("```json")
            lines.append(json.dumps(evaluation["lol_active_vs_idle_menu_share"], indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")

    all_checks = [check for item in evaluations.values() for check in item["checks"]]
    failed = [check for check in all_checks if check["status"] != "PASS"]
    lines.append("## Gesamtstatus")
    lines.append(f"- checks_total: {len(all_checks)}")
    lines.append(f"- checks_failed: {len(failed)}")
    lines.append(f"- status: {'PASS' if not failed else 'FAIL'}")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def run_all_defaults() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    detector = PlaySegmentBoundaryDetector(window_seconds=2.0, visual_sample_seconds=1.0)
    results: Dict[str, Any] = {}
    evaluations: Dict[str, Any] = {}

    for label, spec in DEFAULT_VIDEOS.items():
        path = Path(spec["path"])
        print(f"[G6-2] START label={label} path={path}")
        if not path.exists():
            raise FileNotFoundError(f"missing default video for {label}: {path}")

        result = detector.detect(
            path,
            max_duration_seconds=spec.get("max_duration_seconds"),
            include_raw_windows=False,
        )
        json_path = OUTPUT_DIR / f"{label}_g6_2_segments.json"
        detector.write_json(result, json_path, include_raw_windows=False)

        evaluation = _evaluate_ground_truth(label, result, spec)
        eval_path = OUTPUT_DIR / f"{label}_g6_2_ground_truth.json"
        eval_path.write_text(json.dumps(evaluation, indent=2, ensure_ascii=False), encoding="utf-8")

        results[label] = result
        evaluations[label] = evaluation

        failed = [check for check in evaluation["checks"] if check["status"] != "PASS"]
        print(
            f"[G6-2] DONE label={label} duration={result.analyzed_duration_seconds:.2f}s "
            f"segments={len(result.segments)} checks={len(evaluation['checks'])} failed={len(failed)}"
        )

    report_path = _write_report(results, evaluations)
    all_failed = [
        (label, check)
        for label, evaluation in evaluations.items()
        for check in evaluation["checks"]
        if check["status"] != "PASS"
    ]

    print(f"[G6-2] REPORT {report_path}")
    print(f"[G6-2] STATUS {'PASS' if not all_failed else 'FAIL'} failed={len(all_failed)}")
    return 0 if not all_failed else 2


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-defaults", action="store_true", help="Analyze RL sanity plus full Fortnite/LoL/Minecraft default videos.")
    args = parser.parse_args(argv)

    if not args.all_defaults:
        parser.error("use --all-defaults")

    return run_all_defaults()


if __name__ == "__main__":
    raise SystemExit(main())
