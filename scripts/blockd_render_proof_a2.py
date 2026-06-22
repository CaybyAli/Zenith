from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.final_render_driver import FinalRenderDriver
from core.power_profile import PowerProfile
from core.reaction_focus_decisions import inject_selected_reaction_focus_decisions
from core.smooth_zoom_engine import TARGET_BALANCED, TARGET_GAMEPLAY, ZoomCurve, ZoomKeyframe
from models.edit_timeline import EditTimeline
from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment
from shared.enums import ChannelType


PAIR_ID = "pair_006"
RAW_PATH = ROOT / "learning_corpus" / "pairs" / PAIR_ID / "raw.mp4"
DEFAULT_PICKS_JSON = ROOT / "reports" / "blockd_a2b3a_shadow" / "pair_006_shadow_LOCKED.json"
OUTPUT_DIR = ROOT / "reports" / "blockd_a2b3b_render"
DEFAULT_OUTPUT_PATH = OUTPUT_DIR / "pair_006_a2b3b_proof_v3.mp4"
FFPROBE_PATH = Path(r"D:\Tools\ffmpeg\bin\ffprobe.exe")

CONFIDENCE_FLOOR = 0.80
APPLY_LLM_PICKS_FOR_PROOF_RENDER = True
CLUSTER_MIN_SIZE = 2
CLUSTER_MAX_SIZE = 3
WINDOW_PAD_SECONDS = 4.0
REACTION_LEAD_IN_SECONDS = 0.0
GAMEPLAY_ZOOM = 1.4


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _filtered_candidates(
    report: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    rows = report.get("candidates")
    if not isinstance(rows, list):
        raise RuntimeError("Shadow report has no candidates list")

    counters = {
        "input_candidates": len(rows),
        "excluded_not_real_reaction": 0,
        "excluded_real_below_confidence_floor": 0,
        "excluded_invalid_timing_or_confidence": 0,
        "remaining_after_filters": 0,
    }
    filtered: list[dict[str, Any]] = []
    real_below_floor: list[dict[str, Any]] = []

    for row in rows:
        if not isinstance(row, dict):
            counters["excluded_invalid_timing_or_confidence"] += 1
            continue
        try:
            start = float(row.get("start"))
            end = float(row.get("end"))
            zoom_start = float(row.get("zoom_start"))
            zoom_end = float(row.get("zoom_end"))
            confidence = float(row.get("confidence"))
        except (TypeError, ValueError):
            counters["excluded_invalid_timing_or_confidence"] += 1
            continue

        if end <= start or zoom_end <= zoom_start:
            counters["excluded_invalid_timing_or_confidence"] += 1
            continue

        normalized = {
            **row,
            "start": round(start, 3),
            "end": round(end, 3),
            "zoom_start": round(zoom_start, 3),
            "zoom_end": round(zoom_end, 3),
            "confidence": confidence,
            "friend_span_seconds": round(end - start, 3),
            "zoom_dauer": round(zoom_end - zoom_start, 3),
            "zoom_mode": str(row.get("zoom_mode") or "smooth"),
        }

        if row.get("is_real_reaction") is not True:
            counters["excluded_not_real_reaction"] += 1
            continue

        if confidence < CONFIDENCE_FLOOR:
            counters["excluded_real_below_confidence_floor"] += 1
            real_below_floor.append(normalized)
            continue

        filtered.append(normalized)

    filtered.sort(key=lambda item: (float(item["start"]), float(item["end"])))
    real_below_floor.sort(key=lambda item: (float(item["start"]), float(item["end"])))
    counters["remaining_after_filters"] = len(filtered)
    if len(filtered) < CLUSTER_MIN_SIZE:
        raise RuntimeError(
            f"Only {len(filtered)} candidates after filtering, need at least {CLUSTER_MIN_SIZE}"
        )
    return filtered, real_below_floor, counters


def _densest_cluster(rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    max_size = min(CLUSTER_MAX_SIZE, len(rows))
    for size in range(CLUSTER_MIN_SIZE, max_size + 1):
        for start_index in range(0, len(rows) - size + 1):
            cluster_rows = rows[start_index:start_index + size]
            cluster_start = float(cluster_rows[0]["start"])
            cluster_end = float(cluster_rows[-1]["end"])
            span = cluster_end - cluster_start
            density = float(size) / max(span, 0.001)
            candidates.append(
                {
                    "size": size,
                    "start_index": start_index,
                    "span_seconds": round(span, 3),
                    "density": round(density, 6),
                    "picks": cluster_rows,
                }
            )

    if not candidates:
        raise RuntimeError("No cluster candidates built")

    candidates.sort(
        key=lambda item: (
            -float(item["density"]),
            float(item["span_seconds"]),
            -int(item["size"]),
            float(item["picks"][0]["start"]),
        )
    )
    selected = dict(candidates[0])
    first = selected["picks"][0]
    last = selected["picks"][-1]
    window_start = max(0.0, float(first["start"]) - WINDOW_PAD_SECONDS)
    window_end = float(last["end"]) + WINDOW_PAD_SECONDS
    selected["window_start"] = round(window_start, 3)
    selected["window_end"] = round(window_end, 3)
    selected["window_duration_seconds"] = round(window_end - window_start, 3)
    return selected


def _segment(segment_id: str, job_id: str, start: float, end: float, role: str) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id=job_id,
        candidate_id=None,
        start_time=round(float(start), 3),
        end_time=round(float(end), 3),
        segment_role=role,
        selection_score=1.0,
        notes=["blockd_render_proof_a2"],
    )


def _build_timeline(
    *,
    job_id: str,
    window_start: float,
    window_end: float,
    picks: list[dict[str, Any]],
) -> EditTimeline:
    segments: list[TimelineSegment] = []
    cursor = float(window_start)
    for index, pick in enumerate(picks, start=1):
        focus_start = float(pick["zoom_start"])
        focus_end = float(pick["zoom_end"])
        candidate_index = str(pick.get("candidate_index", index))

        if focus_start > cursor:
            role = "context_before_reaction" if not segments else "context_between_reactions"
            segments.append(
                _segment(
                    f"{PAIR_ID}_context_{index:02d}",
                    job_id,
                    cursor,
                    focus_start,
                    role,
                )
            )

        segments.append(
            _segment(
                f"{PAIR_ID}_reaction_{candidate_index}",
                job_id,
                max(cursor, focus_start),
                focus_end,
                "llm_reaction_gameplay_focus",
            )
        )
        cursor = max(cursor, focus_end)

    if window_end > cursor:
        segments.append(
            _segment(
                f"{PAIR_ID}_post_context",
                job_id,
                cursor,
                window_end,
                "context_after_reaction",
            )
        )

    return EditTimeline(
        timeline_id=f"{PAIR_ID}_a2b3b_proof_window",
        job_id=job_id,
        target_duration=round(window_end - window_start, 3),
        selected_segments=[segment for segment in segments if segment.duration > 0.0],
        timeline_score=1.0,
        timeline_notes=["blockd_a2b3b_context_window"],
    )


def _build_reframe_plan(job_id: str, timeline: EditTimeline) -> ReframePlan:
    return ReframePlan(
        plan_id=f"{timeline.timeline_id}_reframe",
        job_id=job_id,
        timeline_id=timeline.timeline_id,
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        instructions=[
            FramingInstruction(
                instruction_id=f"frame_{segment.segment_id}",
                job_id=job_id,
                timeline_id=timeline.timeline_id,
                segment_id=segment.segment_id,
                focus_kind="balanced",
                layout_kind="balanced_split",
                source_aspect_ratio="32:9",
                target_aspect_ratio="16:9",
                crop_window={"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0},
                notes=["focus_decision_may_override"],
            )
            for segment in timeline.selected_segments
        ],
        plan_score=1.0,
    )


def _apply_a2_focus_window(decision: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    focus_start = float(row["zoom_start"])
    focus_end = float(row["zoom_end"])
    decision["focus_target"] = "gameplay"
    decision["facecam_opacity"] = 0.0
    decision["gameplay_zoom"] = GAMEPLAY_ZOOM
    decision["focus_start_seconds"] = round(focus_start, 3)
    decision["focus_end_seconds"] = round(focus_end, 3)
    decision["focus_duration_seconds"] = round(focus_end - focus_start, 3)
    decision["timestamp"] = round(focus_start + ((focus_end - focus_start) / 2.0), 3)
    decision["lead_in_seconds"] = REACTION_LEAD_IN_SECONDS
    decision["zoom_mode"] = str(row.get("zoom_mode") or "smooth")
    return decision


def _build_zoom_curve(*, window_start: float, window_end: float, picks: list[dict[str, Any]]) -> ZoomCurve:
    keyframes = [ZoomKeyframe(window_start, 1.0, TARGET_BALANCED, "linear")]
    for row in picks:
        focus_start = float(row["zoom_start"])
        focus_end = float(row["zoom_end"])
        keyframes.extend(
            [
                ZoomKeyframe(max(window_start, round(focus_start - 0.001, 3)), 1.0, TARGET_BALANCED, "linear"),
                ZoomKeyframe(focus_start, GAMEPLAY_ZOOM, TARGET_GAMEPLAY, "linear"),
                ZoomKeyframe(focus_end, GAMEPLAY_ZOOM, TARGET_GAMEPLAY, "linear"),
                ZoomKeyframe(min(window_end, round(focus_end + 0.001, 3)), 1.0, TARGET_BALANCED, "linear"),
            ]
        )
    keyframes.append(ZoomKeyframe(window_end, 1.0, TARGET_BALANCED, "linear"))
    return ZoomCurve(keyframes)


def _ffprobe_media(path: Path) -> dict[str, Any]:
    if not FFPROBE_PATH.exists():
        raise RuntimeError(f"ffprobe missing: {FFPROBE_PATH}")
    result = subprocess.run(
        [
            str(FFPROBE_PATH),
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,width,height,channels,sample_rate",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _make_runtime_job(tag: str) -> SimpleNamespace:
    return SimpleNamespace(
        job_id=f"pair_006_a2b3b_proof_{tag}",
        raw_video_path=str(RAW_PATH),
        channel_type=ChannelType.GAMING_MAIN,
        power_profile=PowerProfile.BALANCED,
        focus_decisions=[],
        focus_decisions_count=0,
        profanity_censor_matches=[],
        profanity_censor_report={},
    )


def _inject_runtime_focus_decisions(job: SimpleNamespace, picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not APPLY_LLM_PICKS_FOR_PROOF_RENDER:
        raise RuntimeError("Scoped proof-render apply flag is disabled")

    injected = inject_selected_reaction_focus_decisions(
        job,
        picks,
        gameplay_zoom=GAMEPLAY_ZOOM,
    )
    if len(injected) != len(picks):
        raise RuntimeError(f"Injected {len(injected)} focus decisions for {len(picks)} picks")

    decisions: list[dict[str, Any]] = []
    for decision, row in zip(injected, picks):
        decision = _apply_a2_focus_window(decision, row)
        decision["scoped_apply_flag"] = "APPLY_LLM_PICKS_FOR_PROOF_RENDER"
        decisions.append(decision)
    job.focus_decisions = decisions
    job.focus_decisions_count = len(decisions)
    return decisions


def _pick_report(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_index": row.get("candidate_index"),
        "start": round(float(row["start"]), 3),
        "end": round(float(row["end"]), 3),
        "zoom_start": round(float(row["zoom_start"]), 3),
        "zoom_end": round(float(row["zoom_end"]), 3),
        "confidence": float(row["confidence"]),
        "zoom_mode": str(row.get("zoom_mode") or "smooth"),
        "friend_text": str(row.get("friend_text") or ""),
    }


def _planned_cut_segments(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_index": row.get("candidate_index"),
            "gameplay_crop_start": round(float(row["zoom_start"]), 3),
            "gameplay_crop_end": round(float(row["zoom_end"]), 3),
            "zoom_mode": str(row.get("zoom_mode") or "smooth"),
            "confidence": float(row["confidence"]),
            "friend_text": str(row.get("friend_text") or ""),
        }
        for row in picks
    ]


def _render_window(
    *,
    cluster: dict[str, Any],
    output_path: Path,
    tag: str,
) -> dict[str, Any]:
    picks = list(cluster["picks"])
    window_start = float(cluster["window_start"])
    window_end = float(cluster["window_end"])
    planned_segments = _planned_cut_segments(picks)

    job = _make_runtime_job(tag)
    injected = _inject_runtime_focus_decisions(job, picks)
    timeline = _build_timeline(
        job_id=job.job_id,
        window_start=window_start,
        window_end=window_end,
        picks=picks,
    )
    reframe_plan = _build_reframe_plan(job.job_id, timeline)
    zoom_curve = _build_zoom_curve(window_start=window_start, window_end=window_end, picks=picks)

    rendered_path = Path(
        FinalRenderDriver().render(
            job=job,
            source_path=str(RAW_PATH),
            edit_timeline=timeline,
            reframe_plan=reframe_plan,
            dynamic_edit_plan=None,
            smooth_zoom_curve=zoom_curve,
            output_dir=OUTPUT_DIR,
            facecam_static_tiny=False,
        )
    )
    shutil.copy2(rendered_path, output_path)
    context_path = OUTPUT_DIR / f"{job.job_id}_final_render_driver_context.json"
    context = _load_json(context_path)
    probe = _ffprobe_media(output_path)

    return {
        "target_output_path": str(output_path),
        "driver_output_path": str(rendered_path),
        "context_path": str(context_path),
        "window_start": round(window_start, 3),
        "window_end": round(window_end, 3),
        "window_duration_seconds": round(window_end - window_start, 3),
        "planned_cut_segments": planned_segments,
        "timeline_segments": [
            {
                "segment_id": segment.segment_id,
                "role": segment.segment_role,
                "start": segment.start_time,
                "end": segment.end_time,
                "duration": round(segment.duration, 3),
            }
            for segment in timeline.selected_segments
        ],
        "injected_focus_decisions": injected,
        "zoom_curve": zoom_curve.to_dict(),
        "render_context": {
            "focus_decisions_used": context.get("focus_decisions_used"),
            "smooth_zoom_used": context.get("smooth_zoom_used"),
            "render_layout_counts": context.get("render_layout_counts"),
            "resolved_render_layouts": context.get("resolved_render_layouts"),
            "smooth_zoom_records": context.get("smooth_zoom_records"),
        },
        "ffprobe": probe,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--picks-json", type=Path, default=DEFAULT_PICKS_JSON)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--tag", default="v3")
    args = parser.parse_args(argv[1:])

    picks_json = args.picks_json if args.picks_json.is_absolute() else ROOT / args.picks_json
    output_path = args.out if args.out.is_absolute() else ROOT / args.out
    tag = str(args.tag).strip() or "v3"

    if not RAW_PATH.exists():
        raise RuntimeError(f"Raw video missing: {RAW_PATH}")
    if not picks_json.exists():
        raise RuntimeError(f"Shadow report missing: {picks_json}")

    report = _load_json(picks_json)
    filtered, real_below_floor, counters = _filtered_candidates(report)
    cluster = _densest_cluster(filtered)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("A2b-3b Artifact-Locked Proof Render")
    print(f"pair_id={PAIR_ID}")
    print(f"raw_path={RAW_PATH}")
    print(f"picks_json={picks_json}")
    print(f"output_path={output_path}")
    print(f"render_tag={tag}")
    print(f"confidence_floor={CONFIDENCE_FLOOR:.2f}")
    print(f"scoped_apply_flag=APPLY_LLM_PICKS_FOR_PROOF_RENDER:{APPLY_LLM_PICKS_FOR_PROOF_RENDER}")
    print(f"filter_counters={json.dumps(counters, ensure_ascii=False, sort_keys=True)}")

    print("kept_picks_ge_floor=")
    for row in filtered:
        print(json.dumps(_pick_report(row), ensure_ascii=False, sort_keys=True))

    print("real_reactions_dropped_below_floor=")
    for row in real_below_floor:
        print(json.dumps(_pick_report(row), ensure_ascii=False, sort_keys=True))

    print(
        "selected_cluster="
        f"size={cluster['size']} span={cluster['span_seconds']:.3f} "
        f"density={cluster['density']:.6f} "
        f"window={cluster['window_start']:.3f}-{cluster['window_end']:.3f} "
        f"duration={cluster['window_duration_seconds']:.3f}"
    )
    print("selected_cluster_picks=")
    for row in cluster["picks"]:
        print(json.dumps(_pick_report(row), ensure_ascii=False, sort_keys=True))

    proof = _render_window(cluster=cluster, output_path=output_path, tag=tag)
    print("planned_cut_segments=")
    print(json.dumps(proof["planned_cut_segments"], indent=2, ensure_ascii=False, sort_keys=True))
    print("render_proof=")
    print(json.dumps(proof, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
