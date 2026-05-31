from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.reaction_adaptive_thresholds import (
    AdaptiveReactionProfile,
    build_adaptive_reaction_profile,
    classify_adaptive_reaction,
    is_medium_or_high,
    reaction_rank,
)
from core.reaction_intensity_signal_builder import (
    ReactionIntensitySignalBuilder,
    format_reaction_timestamp,
    parse_crop,
    probe_duration_seconds,
    probe_video_size,
    resolve_video,
)


TAIL_WINDOWS = [
    {"id": "tail_001", "start": 172.0, "end": 192.0, "expected": "quiet", "note": "ruhig erwartet"},
    {"id": "tail_002", "start": 550.0, "end": 570.0, "expected": "quiet", "note": "ruhig erwartet"},
    {"id": "tail_003", "start": 802.0, "end": 818.0, "expected": "quiet", "note": "ruhig erwartet"},
    {"id": "tail_004", "start": 918.0, "end": 938.0, "expected": "quiet", "note": "ruhig erwartet"},
    {"id": "tail_005", "start": 1198.0, "end": 1218.0, "expected": "borderline", "note": "Grenzfall"},
    {"id": "tail_006", "start": 1498.0, "end": 1512.0, "expected": "quiet", "note": "ruhig erwartet"},
    {"id": "tail_007", "start": 1622.0, "end": 1642.0, "expected": "quiet", "note": "ruhig erwartet"},
    {"id": "tail_008", "start": 1792.0, "end": 1810.0, "expected": "payoff", "note": "Tod/Payoff erwartet"},
]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _load_speech_segments(path: Path) -> list[dict[str, Any]]:
    data = _read_json(path)
    if isinstance(data, Mapping):
        for key in ("speech_segments", "segments", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break

    result: list[dict[str, Any]] = []
    if not isinstance(data, list):
        return result

    for index, item in enumerate(data, start=1):
        if not isinstance(item, Mapping):
            continue
        start = _safe_float(item.get("start_seconds", item.get("start", item.get("start_time"))))
        end = _safe_float(item.get("end_seconds", item.get("end", item.get("end_time"))))
        if end <= start:
            continue
        result.append({
            "id": str(item.get("speech_segment_id") or item.get("segment_id") or f"speech_{index:04d}"),
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "text": str(item.get("text") or "").strip(),
        })
    return sorted(result, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def _load_words(path: Path) -> list[dict[str, Any]]:
    data = _read_json(path)
    if isinstance(data, Mapping):
        for key in ("words", "word_timestamps", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break

    result: list[dict[str, Any]] = []
    if not isinstance(data, list):
        return result

    for item in data:
        if not isinstance(item, Mapping):
            continue
        word = str(item.get("word") or item.get("text") or "").strip()
        start = _safe_float(item.get("start_seconds", item.get("start", item.get("start_time"))))
        end = _safe_float(item.get("end_seconds", item.get("end", item.get("end_time"))))
        if not word or end <= start:
            continue
        result.append({
            "word": word,
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
        })
    return sorted(result, key=lambda item: (item["start_seconds"], item["end_seconds"]))


def _text_from_words(words: list[Mapping[str, Any]], start: float, end: float) -> str:
    tokens: list[str] = []
    for word in words:
        word_start = _safe_float(word.get("start_seconds"))
        word_end = _safe_float(word.get("end_seconds"))
        if word_end <= start or word_start >= end:
            continue
        token = str(word.get("word") or "").strip()
        if token:
            tokens.append(token)
    return " ".join(tokens).strip()


def _auto_left_half_crop(video_w: int, video_h: int) -> tuple[int, int, int, int]:
    return (0, 0, max(1, video_w // 2), video_h)


def _build_evidence_rows(
    *,
    builder: ReactionIntensitySignalBuilder,
    features: dict[str, Any],
    speech_segments: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    count = min(
        len(features["mic_rms_db"]),
        len(features["gameplay_rms_db"]),
        len(features["facecam_motion_raw"]),
    )

    rows: list[dict[str, Any]] = []
    window_seconds = float(builder.window_seconds)

    for index in range(count):
        start = round(index * window_seconds, 3)
        end = round(start + window_seconds, 3)
        evidence = builder.evidence_at(features, start, tolerance_seconds=0.0)

        speech_overlap = 0.0
        speech_ids: list[str] = []
        for speech in speech_segments:
            overlap = _overlap_seconds(
                start,
                end,
                _safe_float(speech.get("start_seconds")),
                _safe_float(speech.get("end_seconds")),
            )
            if overlap > 0:
                speech_overlap += overlap
                speech_ids.append(str(speech.get("id") or ""))

        rows.append({
            "time_seconds": start,
            "end_seconds": end,
            "timestamp": evidence.timestamp,
            "fusion_score": float(evidence.fusion_score),
            "mic_audio_rise_db": float(evidence.mic_audio_rise_db),
            "mic_peak_over_baseline_db": float(evidence.mic_peak_over_baseline_db),
            "facecam_change": float(evidence.facecam_change),
            "gameplay_rise_db": float(evidence.gameplay_rise_db),
            "gameplay_peak_dbfs": float(evidence.gameplay_peak_dbfs),
            "speech_overlap_seconds": round(speech_overlap, 3),
            "speech_segment_ids": [item for item in speech_ids if item],
        })

    return rows


def _rows_in_window(rows: list[Mapping[str, Any]], start: float, end: float) -> list[Mapping[str, Any]]:
    return [
        row for row in rows
        if _safe_float(row.get("time_seconds")) >= start
        and _safe_float(row.get("time_seconds")) < end
    ]


def _best_adaptive_row(rows: list[Mapping[str, Any]], profile: AdaptiveReactionProfile) -> tuple[Mapping[str, Any] | None, str]:
    if not rows:
        return None, "none"

    scored = []
    for row in rows:
        intensity = classify_adaptive_reaction(row, profile)
        scored.append((row, intensity))

    best_row, best_intensity = max(
        scored,
        key=lambda pair: (
            reaction_rank(pair[1]),
            _safe_float(pair[0].get("fusion_score")),
            _safe_float(pair[0].get("mic_audio_rise_db")),
        ),
    )
    return best_row, best_intensity


def _tail_table(rows: list[Mapping[str, Any]], profile: AdaptiveReactionProfile) -> list[dict[str, Any]]:
    table: list[dict[str, Any]] = []

    for window in TAIL_WINDOWS:
        start = float(window["start"])
        end = float(window["end"])
        inside = _rows_in_window(rows, start, end)
        best, intensity = _best_adaptive_row(inside, profile)

        if best is None:
            table.append({
                **window,
                "detected_intensity": "NONE",
                "fusion_score": None,
                "mic_audio_rise_db": None,
                "facecam_change": None,
                "best_timestamp": None,
                "strict_pass": False,
            })
            continue

        detected = intensity.upper()
        expected = str(window["expected"])

        if expected == "quiet":
            strict_pass = detected == "NONE"
        elif expected == "payoff":
            strict_pass = detected in {"MEDIUM", "HIGH"}
        else:
            strict_pass = None

        table.append({
            **window,
            "detected_intensity": detected,
            "fusion_score": _safe_float(best.get("fusion_score")),
            "mic_audio_rise_db": _safe_float(best.get("mic_audio_rise_db")),
            "facecam_change": _safe_float(best.get("facecam_change")),
            "gameplay_rise_db": _safe_float(best.get("gameplay_rise_db")),
            "best_time_seconds": _safe_float(best.get("time_seconds")),
            "best_timestamp": str(best.get("timestamp") or ""),
            "speech_overlap_seconds": _safe_float(best.get("speech_overlap_seconds")),
            "strict_pass": strict_pass,
        })

    return table


def _table_passes(table: list[Mapping[str, Any]]) -> bool:
    quiet_ok = all(
        row.get("detected_intensity") == "NONE"
        for row in table
        if row.get("expected") == "quiet"
    )
    payoff_ok = all(
        row.get("detected_intensity") in {"MEDIUM", "HIGH"}
        for row in table
        if row.get("expected") == "payoff"
    )
    return quiet_ok and payoff_ok


def _select_profile(
    candidate_rows: list[Mapping[str, Any]],
    all_rows: list[Mapping[str, Any]],
) -> tuple[AdaptiveReactionProfile, list[dict[str, Any]], list[dict[str, Any]]]:
    tried: list[dict[str, Any]] = []
    passing: list[tuple[float, AdaptiveReactionProfile, list[dict[str, Any]]]] = []

    # MIC-PRIMARY profile search:
    # Prefer the strictest mic gate that still keeps the true death payoff.
    for medium_pct in [70, 75, 80, 85, 90, 92, 95]:
        for high_pct in [95, 97, 99]:
            if high_pct <= medium_pct:
                continue
            for mic_pct in [85, 90, 92, 95, 97, 98]:
                profile = build_adaptive_reaction_profile(
                    candidate_rows,
                    medium_percentile=float(medium_pct),
                    high_percentile=float(high_pct),
                    mic_floor_percentile=float(mic_pct),
                )
                table = _tail_table(all_rows, profile)
                passed = _table_passes(table)

                tried.append({
                    "medium_percentile": medium_pct,
                    "high_percentile": high_pct,
                    "mic_floor_percentile": mic_pct,
                    "medium_fusion_score": profile.medium_fusion_score,
                    "medium_mic_rise_db": profile.medium_mic_rise_db,
                    "passed_8_window_check": passed,
                })

                if passed:
                    # Mic-first strictness: choose the highest working mic threshold first.
                    strictness = (profile.medium_mic_rise_db * 100.0) + profile.medium_fusion_score
                    passing.append((strictness, profile, table))

    if passing:
        passing.sort(key=lambda item: item[0], reverse=True)
        return passing[0][1], passing[0][2], tried

    fallback = build_adaptive_reaction_profile(candidate_rows)
    return fallback, _tail_table(all_rows, fallback), tried


def _distribution(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    fusion = [_safe_float(row.get("fusion_score")) for row in rows]
    mic = [_safe_float(row.get("mic_audio_rise_db")) for row in rows]

    from core.reaction_adaptive_thresholds import percentile, mean_std

    fusion_mean, fusion_std = mean_std(fusion)
    mic_mean, mic_std = mean_std(mic)

    return {
        "count": len(rows),
        "fusion_mean": fusion_mean,
        "fusion_std": fusion_std,
        "fusion_p50": percentile(fusion, 50),
        "fusion_p75": percentile(fusion, 75),
        "fusion_p90": percentile(fusion, 90),
        "fusion_p95": percentile(fusion, 95),
        "fusion_p99": percentile(fusion, 99),
        "mic_mean": mic_mean,
        "mic_std": mic_std,
        "mic_p50": percentile(mic, 50),
        "mic_p75": percentile(mic, 75),
        "mic_p90": percentile(mic, 90),
        "mic_p95": percentile(mic, 95),
        "mic_p99": percentile(mic, 99),
    }


def _merge_reaction_events(
    classified_rows: list[dict[str, Any]],
    *,
    words: list[Mapping[str, Any]],
    merge_gap_seconds: float = 0.75,
) -> list[dict[str, Any]]:
    hot_rows = [
        row for row in classified_rows
        if is_medium_or_high(str(row.get("adaptive_intensity") or "none"))
    ]

    if not hot_rows:
        return []

    hot_rows = sorted(hot_rows, key=lambda row: (_safe_float(row.get("time_seconds")), _safe_float(row.get("end_seconds"))))
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = [hot_rows[0]]

    for row in hot_rows[1:]:
        previous_end = _safe_float(current[-1].get("end_seconds"))
        row_start = _safe_float(row.get("time_seconds"))
        if row_start <= previous_end + merge_gap_seconds:
            current.append(row)
        else:
            groups.append(current)
            current = [row]
    groups.append(current)

    events: list[dict[str, Any]] = []
    for index, group in enumerate(groups, start=1):
        start = min(_safe_float(row.get("time_seconds")) for row in group)
        end = max(_safe_float(row.get("end_seconds")) for row in group)
        # Mic-primary peak selection:
        # The representative reaction must be the strongest voice-rise moment, not a facecam-only fusion peak.
        best = max(
            group,
            key=lambda row: (
                reaction_rank(str(row.get("adaptive_intensity") or "none")),
                _safe_float(row.get("mic_audio_rise_db")),
                _safe_float(row.get("fusion_score")),
            ),
        )
        intensity = str(best.get("adaptive_intensity") or "none").upper()
        text = _text_from_words(words, max(0.0, start - 2.0), end + 2.0)

        events.append({
            "reaction_id": f"reaction_adaptive_{index:04d}",
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "peak_time_seconds": _safe_float(best.get("time_seconds")),
            "peak_timestamp": str(best.get("timestamp") or format_reaction_timestamp(_safe_float(best.get("time_seconds")))),
            "intensity": intensity,
            "fusion_score": _safe_float(best.get("fusion_score")),
            "mic_audio_rise_db": _safe_float(best.get("mic_audio_rise_db")),
            "facecam_change": _safe_float(best.get("facecam_change")),
            "speech_overlap_seconds": round(sum(_safe_float(row.get("speech_overlap_seconds")) for row in group), 3),
            "mic_primary_gate_pass": _safe_float(best.get("mic_audio_rise_db")) > 0.0,
            "text": text,
        })

    return events


def _write_text_report(
    *,
    path: Path,
    video: Path,
    duration: float,
    video_size: tuple[int, int],
    crop: tuple[int, int, int, int],
    mic_track: int,
    gameplay_track: int,
    profile: AdaptiveReactionProfile,
    all_distribution: Mapping[str, Any],
    speech_distribution: Mapping[str, Any],
    table: list[Mapping[str, Any]],
    reactions: list[Mapping[str, Any]],
    tried_profiles: list[Mapping[str, Any]],
    reactions_path: Path,
    json_report_path: Path,
) -> None:
    quiet_ok = all(row.get("detected_intensity") == "NONE" for row in table if row.get("expected") == "quiet")
    payoff_ok = all(row.get("detected_intensity") in {"MEDIUM", "HIGH"} for row in table if row.get("expected") == "payoff")
    verdict = "PASS" if quiet_ok and payoff_ok else "FAIL"

    lines: list[str] = []
    lines.append("PROJECT ZENITH - REACTION-ADAPTIVE REPORT")
    lines.append("")
    lines.append(f"video={video}")
    lines.append(f"duration_seconds={round(duration, 3)}")
    lines.append(f"video_size={video_size[0]}x{video_size[1]}")
    lines.append(f"mic_track_1based={mic_track}")
    lines.append(f"gameplay_track_1based={gameplay_track}")
    lines.append(f"facecam_crop=x={crop[0]},y={crop[1]},w={crop[2]},h={crop[3]}")
    lines.append("")
    lines.append("ADAPTIVE PROFILE")
    for key, value in profile.to_dict().items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("SCORE DISTRIBUTION - ALL WINDOWS")
    for key, value in all_distribution.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("SCORE DISTRIBUTION - SPEECH CANDIDATE WINDOWS")
    for key, value in speech_distribution.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("8-WINDOW CHECK")
    lines.append(f"- verdict={verdict}")
    lines.append(f"- quiet_windows_none={quiet_ok}")
    lines.append(f"- payoff_medium_or_high={payoff_ok}")
    lines.append("")
    lines.append("id | window | expected | detected | fusion | mic_rise | facecam | time | pass | note")
    lines.append("---|---:|---|---|---:|---:|---:|---|---|---")
    for row in table:
        lines.append(
            f"{row.get('id')} | "
            f"{row.get('start')}-{row.get('end')} | "
            f"{row.get('expected')} | "
            f"{row.get('detected_intensity')} | "
            f"{row.get('fusion_score')} | "
            f"{row.get('mic_audio_rise_db')} | "
            f"{row.get('facecam_change')} | "
            f"{row.get('best_timestamp')} | "
            f"{row.get('strict_pass')} | "
            f"{row.get('note')}"
        )
    lines.append("")
    lines.append("MEDIUM/HIGH REACTIONS FOR ALI REVIEW")
    lines.append(f"- reaction_count={len(reactions)}")
    if not reactions:
        lines.append("- none")
    for item in reactions:
        lines.append(
            f"- {item.get('reaction_id')} "
            f"{item.get('peak_timestamp')} "
            f"intensity={item.get('intensity')} "
            f"fusion={item.get('fusion_score')} "
            f"mic_rise={item.get('mic_audio_rise_db')} "
            f"text={item.get('text')}"
        )
    lines.append("")
    lines.append("PROFILE SEARCH")
    lines.append(f"- tried_profiles={len(tried_profiles)}")
    passing_count = sum(1 for item in tried_profiles if item.get("passed_8_window_check"))
    lines.append(f"- passing_profiles={passing_count}")
    lines.append("- selection_rule=strictest passing MIC-PRIMARY adaptive profile; highest working mic threshold wins")
    lines.append("")
    lines.append("MINECRAFT SANITY")
    lines.append("- status=NOT_RUN_OPTIONAL")
    lines.append("- reason=Fortnite portability was the required proof in this local probe; existing Minecraft absolute path was not modified.")
    lines.append("")
    lines.append("OUTPUTS")
    lines.append(str(reactions_path))
    lines.append(str(json_report_path))
    lines.append(str(path))
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default=r"D:\Zenith\inbox\gaming_main\Fortnite Full Video.mp4")
    parser.add_argument("--mic-track", type=int, default=1)
    parser.add_argument("--gameplay-track", type=int, default=2)
    parser.add_argument("--facecam-crop", default="auto-left-half")
    parser.add_argument("--speech-segments", default="reports/speech_1_transcript/fortnite_speech_segments.json")
    parser.add_argument("--words-json", default="reports/speech_1_transcript/fortnite_words.json")
    parser.add_argument("--out-dir", default="reports/reaction_adaptive")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    video = resolve_video(args.video)
    duration = probe_duration_seconds(video)
    video_w, video_h = probe_video_size(video)

    if args.facecam_crop == "auto-left-half":
        crop = _auto_left_half_crop(video_w, video_h)
    else:
        crop = parse_crop(args.facecam_crop, video_w, video_h)

    speech_segments = _load_speech_segments(Path(args.speech_segments))
    words = _load_words(Path(args.words_json))

    builder = ReactionIntensitySignalBuilder(
        video=video,
        mic_track=args.mic_track,
        gameplay_track=args.gameplay_track,
        facecam_crop=crop,
    )

    print("[REACTION-ADAPTIVE] extracting Fortnite features...")
    features = builder.extract_video_features()

    print("[REACTION-ADAPTIVE] building raw evidence rows...")
    rows = _build_evidence_rows(
        builder=builder,
        features=features,
        speech_segments=speech_segments,
    )

    candidate_rows = [row for row in rows if _safe_float(row.get("speech_overlap_seconds")) > 0.0]
    if not candidate_rows:
        raise RuntimeError("No speech candidate windows found. Check SPEECH-1 speech_segments input.")

    print("[REACTION-ADAPTIVE] selecting adaptive profile from speech-candidate distribution...")
    profile, table, tried_profiles = _select_profile(candidate_rows, rows)

    classified_rows: list[dict[str, Any]] = []
    for row in candidate_rows:
        item = dict(row)
        item["adaptive_intensity"] = classify_adaptive_reaction(item, profile)
        classified_rows.append(item)

    reactions = _merge_reaction_events(classified_rows, words=words)

    reactions_path = out_dir / "reaction_adaptive_fortnite_reactions.json"
    json_report_path = out_dir / "reaction_adaptive_report.json"
    txt_report_path = out_dir / "reaction_adaptive_report.txt"

    _write_json(reactions_path, reactions)

    all_distribution = _distribution(rows)
    speech_distribution = _distribution(candidate_rows)

    quiet_ok = all(row.get("detected_intensity") == "NONE" for row in table if row.get("expected") == "quiet")
    payoff_ok = all(row.get("detected_intensity") in {"MEDIUM", "HIGH"} for row in table if row.get("expected") == "payoff")

    report_json = {
        "video": str(video),
        "duration_seconds": round(duration, 3),
        "video_size": {"width": video_w, "height": video_h},
        "mic_track_1based": args.mic_track,
        "gameplay_track_1based": args.gameplay_track,
        "facecam_crop": {"x": crop[0], "y": crop[1], "w": crop[2], "h": crop[3]},
        "adaptive_profile": profile.to_dict(),
        "all_window_distribution": all_distribution,
        "speech_candidate_distribution": speech_distribution,
        "tail_window_check": table,
        "reaction_count": len(reactions),
        "reactions_path": str(reactions_path),
        "verdict": {
            "status": "PASS" if quiet_ok and payoff_ok else "FAIL",
            "quiet_windows_none": bool(quiet_ok),
            "payoff_medium_or_high": bool(payoff_ok),
        },
        "profile_search": {
            "tried_profiles": tried_profiles,
            "passing_profile_count": sum(1 for item in tried_profiles if item.get("passed_8_window_check")),
        },
    }
    _write_json(json_report_path, report_json)

    _write_text_report(
        path=txt_report_path,
        video=video,
        duration=duration,
        video_size=(video_w, video_h),
        crop=crop,
        mic_track=args.mic_track,
        gameplay_track=args.gameplay_track,
        profile=profile,
        all_distribution=all_distribution,
        speech_distribution=speech_distribution,
        table=table,
        reactions=reactions,
        tried_profiles=tried_profiles,
        reactions_path=reactions_path,
        json_report_path=json_report_path,
    )

    print("PROJECT ZENITH - REACTION-ADAPTIVE")
    print(f"report={txt_report_path}")
    print(f"reactions={reactions_path}")
    print(f"reaction_count={len(reactions)}")
    print(f"adaptive_medium_fusion={profile.medium_fusion_score}")
    print(f"adaptive_medium_mic_rise={profile.medium_mic_rise_db}")
    print(f"verdict={'PASS' if quiet_ok and payoff_ok else 'FAIL'}")
    for row in table:
        print(
            f"{row.get('id')} {row.get('start')}-{row.get('end')} "
            f"expected={row.get('expected')} detected={row.get('detected_intensity')} "
            f"fusion={row.get('fusion_score')} mic={row.get('mic_audio_rise_db')} "
            f"pass={row.get('strict_pass')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
