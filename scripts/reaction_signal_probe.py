from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.reaction_intensity_signal_builder import (
    ReactionIntensitySignalBuilder,
    format_reaction_timestamp,
    parse_crop,
    probe_duration_seconds,
    probe_video_size,
    resolve_video,
    summarize_distribution,
    threshold_dict,
)
from tests.reaction_signal_ground_truth import QUIET_NEGATIVES, all_ground_truth


def _write_text_report(report: dict, path: Path) -> None:
    thresholds = report["calibrated_thresholds"]
    summary = report["validation_summary"]
    game = report["gameplay_honesty_check"]
    distribution = report["distribution"]

    lines = []
    lines.append("STUFE D - REACTION INTENSITY SIGNAL PROBE")
    lines.append(f"Video: {report['video']}")
    lines.append(f"Duration seconds: {report['duration_seconds']}")
    lines.append(f"Mic track confirmed: {report['confirmed_tracks']['ali_mic']}")
    lines.append(f"Gameplay track confirmed for old Minecraft video: {report['confirmed_tracks']['gameplay']}")
    lines.append(f"Facecam crop confirmed: {report['facecam_crop']}")
    lines.append("")
    lines.append("Calibrated thresholds:")
    for key, value in thresholds.items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("Validation summary:")
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append(f"Match tolerance seconds: {report['match_tolerance_seconds']}")
    lines.append("")
    lines.append("Missed HIGH/MEDIUM reactions:")
    if report["missed_high_medium"]:
        for miss in report["missed_high_medium"]:
            ev = miss["evidence"]
            lines.append(
                f"- {miss['id']} {miss['timestamp']} expected={miss['expected_intensity']} "
                f"reason={miss['reason']} mic_rise={ev['mic_audio_rise_db']} "
                f"fusion={ev['fusion_score']} facecam={ev['facecam_change']}"
            )
    else:
        lines.append("- none")
    lines.append("")
    lines.append("Gameplay honesty check:")
    lines.append(f"- timestamp: {game['timestamp']}")
    lines.append(f"- gameplay_peak_dbfs: {game['gameplay_peak_dbfs']}")
    lines.append(f"- gameplay_rise_db: {game['gameplay_rise_db']}")
    lines.append(f"- mic_audio_rise_db: {game['mic_audio_rise_db']}")
    lines.append(f"- detected_event: {game['detected_event']}")
    lines.append(f"- pass: {game['pass']}")

    lines.append("")
    lines.append("Distribution over full video:")
    for key, value in distribution.items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("Ground truth results:")
    lines.append("id  | label      | expected | timestamp    | event | detected | conf  | pass | mic_rise | facecam | gameplay | note")
    lines.append("-" * 132)
    for row in report["ground_truth_results"]:
        lines.append(
            f"{row['id']:<3} | "
            f"{row['label']:<10} | "
            f"{str(row.get('intensity', '')):<8} | "
            f"{row['timestamp']:<12} | "
            f"{str(row['detected_event']):<5} | "
            f"{row['detected_intensity']:<8} | "
            f"{row['confidence']:<5.2f} | "
            f"{str(row['pass']):<4} | "
            f"{row['evidence']['mic_audio_rise_db']:<8.2f} | "
            f"{row['evidence']['facecam_change']:<7.3f} | "
            f"{row['evidence']['gameplay_rise_db']:<8.2f} | "
            f"{row.get('note', '')}"
        )

    lines.append("")
    lines.append(f"JSON report: {report['json_report_path']}")
    lines.append(f"Window JSONL: {report['window_jsonl_path']}")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="Minecraft Full Video.mp4")
    ap.add_argument("--mic-track", type=int, default=1)
    ap.add_argument("--gameplay-track", type=int, default=3)
    ap.add_argument("--facecam-crop", default="0,0,1150,1080")
    args = ap.parse_args()

    out_dir = Path("reports") / "reaction_signal"
    out_dir.mkdir(parents=True, exist_ok=True)

    video = resolve_video(args.video)
    duration = probe_duration_seconds(video)
    video_w, video_h = probe_video_size(video)
    crop = parse_crop(args.facecam_crop, video_w, video_h)

    builder = ReactionIntensitySignalBuilder(
        video=video,
        mic_track=args.mic_track,
        gameplay_track=args.gameplay_track,
        facecam_crop=crop,
    )

    print("[Stage D] Extracting mic/gameplay audio + facecam motion features...")
    features = builder.extract_video_features()

    gt = all_ground_truth()
    thresholds = builder.calibrate_thresholds(features, gt)
    gt_results = builder.evaluate_ground_truth(features, thresholds, gt)

    reaction_rows = [r for r in gt_results if r["label"] == "reaction"]
    hm_rows = [
        r for r in reaction_rows
        if str(r.get("intensity", "")).lower() in {"high", "medium"}
    ]
    low_rows = [
        r for r in reaction_rows
        if str(r.get("intensity", "")).lower() == "low"
    ]
    negative_rows = [r for r in gt_results if r["label"] == "negative"]
    dont_care_rows = [r for r in gt_results if r["label"] == "dont_care"]

    game_check = builder.find_gameplay_honesty_check(features, thresholds, QUIET_NEGATIVES)

    print("[Stage D] Building full-video window output...")
    window_rows = builder.build_window_rows(features, thresholds)
    distribution = summarize_distribution(window_rows, window_seconds=builder.window_seconds)

    json_path = out_dir / "stufe_e_reaction_signal_report.json"
    txt_path = out_dir / "stufe_e_reaction_signal_report.txt"
    jsonl_path = out_dir / "stufe_e_reaction_windows.jsonl"

    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in window_rows:
            f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")

    hm_pass = sum(1 for r in hm_rows if r["pass"])
    reaction_pass = sum(1 for r in reaction_rows if r["pass"])
    low_pass = sum(1 for r in low_rows if r["pass"])
    neg_pass = sum(1 for r in negative_rows if r["pass"])

    missed_high_medium = []
    for row in hm_rows:
        if row["pass"]:
            continue

        reasons = []
        if row["evidence"]["mic_audio_rise_db"] < thresholds.event_mic_rise_db:
            reasons.append(
                f"mic_rise {row['evidence']['mic_audio_rise_db']} < threshold {thresholds.event_mic_rise_db}"
            )
        if row["evidence"]["fusion_score"] < thresholds.event_fusion_score:
            reasons.append(
                f"fusion {row['evidence']['fusion_score']} < threshold {thresholds.event_fusion_score}"
            )
        if row["evidence"]["facecam_change"] < thresholds.facecam_motion_hint:
            reasons.append(
                f"facecam_change {row['evidence']['facecam_change']} < hint {thresholds.facecam_motion_hint}"
            )
        if not reasons:
            reasons.append("borderline miss under precision-biased thresholds")

        missed_high_medium.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "expected_intensity": row.get("intensity", ""),
            "note": row.get("note", ""),
            "reason": "; ".join(reasons),
            "evidence": row["evidence"],
        })

    precision_negative_details = [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "pass": row["pass"],
            "detected_event": row["detected_event"],
            "mic_audio_rise_db": row["evidence"]["mic_audio_rise_db"],
            "fusion_score": row["evidence"]["fusion_score"],
            "note": row.get("note", ""),
        }
        for row in negative_rows
    ]

    report = {
        "stage": "E_calibrated_reaction_intensity_signal_validation",
        "video": str(video),
        "duration_seconds": round(duration, 3),
        "video_size": {"width": video_w, "height": video_h},
        "confirmed_tracks": {
            "ali_mic": args.mic_track,
            "gameplay": args.gameplay_track,
            "note": "Old Minecraft test video uses track 1=Ali mic, track 2=Discord, track 3=Gameplay, track 4=empty. New OBS config is different.",
        },
        "facecam_crop": {"x": crop[0], "y": crop[1], "w": crop[2], "h": crop[3]},
        "baselines": features["baselines"],
        "calibrated_thresholds": threshold_dict(thresholds),
        "match_tolerance_seconds": 1.5,
        "validation_summary": {
            "reaction_total": len(reaction_rows),
            "reaction_pass": reaction_pass,
            "reaction_recall": round(reaction_pass / max(1, len(reaction_rows)), 4),
            "high_medium_total": len(hm_rows),
            "high_medium_pass": hm_pass,
            "high_medium_recall": round(hm_pass / max(1, len(hm_rows)), 4),
            "low_total_precision_biased_optional": len(low_rows),
            "low_pass_optional": low_pass,
            "precision_negative_total": len(negative_rows),
            "precision_negative_pass": neg_pass,
            "precision_negative_false_positive": len(negative_rows) - neg_pass,
            "dont_care_total_not_precision": len(dont_care_rows),
            "gameplay_honesty_pass": bool(game_check["pass"]),
            "missed_high_medium_count": len(missed_high_medium),
            "notes": [
                "Precision-biased calibration: LOW misses are acceptable.",
                "Outro marks 29/30 are dont_care and are not precision failures.",
                "Ground-truth matching uses +/- 1.5 seconds around Ali marks, not exact frame matching.",
                "G6 is not loaded in this additive probe; g6_state is reported as not_loaded_stage_d_probe.",
                "Old Minecraft test video uses gameplay track 3. Track 4 is empty in this file.",
            ],
        },
        "missed_high_medium": missed_high_medium,
        "precision_negative_details": precision_negative_details,
        "gameplay_honesty_check": game_check,
        "distribution": distribution,
        "ground_truth_results": gt_results,
        "json_report_path": str(json_path),
        "text_report_path": str(txt_path),
        "window_jsonl_path": str(jsonl_path),
    }

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_text_report(report, txt_path)

    print("")
    print("STUFE E SUMMARY")
    print(f"Threshold event_mic_rise_db: {thresholds.event_mic_rise_db}")
    print(f"Threshold event_fusion_score: {thresholds.event_fusion_score}")
    print(f"HIGH/MEDIUM recall: {hm_pass}/{len(hm_rows)} = {report['validation_summary']['high_medium_recall']}")
    print(f"ALL reaction recall: {reaction_pass}/{len(reaction_rows)} = {report['validation_summary']['reaction_recall']}")
    print(f"Precision negatives: {neg_pass}/{len(negative_rows)} pass")
    print(f"False positives on negatives: {report['validation_summary']['precision_negative_false_positive']}")
    print(f"Gameplay honesty pass: {game_check['pass']} at {game_check['timestamp']}")
    print(f"Distribution: {distribution}")
    print("")
    print(f"JSON report: {json_path}")
    print(f"TXT report: {txt_path}")
    print(f"Window JSONL: {jsonl_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
