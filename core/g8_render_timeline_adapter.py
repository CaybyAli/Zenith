from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from models.edit_timeline import EditTimeline
from models.timeline_segment import TimelineSegment


def _safe_float(value: Any, *, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid float for {field_name}: {value!r}") from exc


def load_g8_timeline_plan(plan_path: str | Path) -> dict[str, Any]:
    path = Path(plan_path)
    if not path.exists():
        raise FileNotFoundError(f"G8 timeline plan not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    timeline_segments = data.get("timeline_segments")
    if not isinstance(timeline_segments, list) or not timeline_segments:
        raise ValueError(f"G8 timeline plan has no timeline_segments: {path}")

    return data


def resolve_g8_plan_path_from_env() -> Path | None:
    explicit = os.environ.get("ZENITH_G8_TIMELINE_PLAN_PATH", "").strip()
    if explicit:
        path = Path(explicit)
        if path.exists():
            return path
        raise FileNotFoundError(f"ZENITH_G8_TIMELINE_PLAN_PATH does not exist: {path}")

    label = os.environ.get("ZENITH_G8_TIMELINE_PLAN_LABEL", "").strip()
    if label:
        path = Path("reports") / "g8_assembly" / f"{label}_g8_timeline_plan.json"
        if path.exists():
            return path
        raise FileNotFoundError(f"ZENITH_G8_TIMELINE_PLAN_LABEL not found: {path}")

    candidates = sorted(Path("reports/g8_assembly").glob("*_g8_timeline_plan.json"))
    planned = []
    for path in candidates:
        try:
            data = load_g8_timeline_plan(path)
        except Exception:
            continue
        if str(data.get("status") or "").startswith("planned"):
            planned.append(path)

    if planned:
        return planned[0]
    return candidates[0] if candidates else None


def build_edit_timeline_from_g8_plan(
    *,
    job_id: str,
    plan_path: str | Path,
) -> EditTimeline:
    path = Path(plan_path)
    data = load_g8_timeline_plan(path)

    duration_contract = data.get("duration_contract") or {}
    planned_duration = _safe_float(
        duration_contract.get("planned_output_duration_seconds", 0.0),
        field_name="duration_contract.planned_output_duration_seconds",
    )

    segments: list[TimelineSegment] = []
    for index, raw in enumerate(data["timeline_segments"], start=1):
        start = _safe_float(raw.get("start_seconds"), field_name=f"timeline_segments[{index}].start_seconds")
        end = _safe_float(raw.get("end_seconds"), field_name=f"timeline_segments[{index}].end_seconds")
        if end <= start:
            raise ValueError(f"G8 segment {index} has invalid time range: {start} -> {end}")

        segment_id = str(raw.get("segment_id") or f"g8_segment_{index:03d}")
        block_id = str(raw.get("block_id") or "")
        state = str(raw.get("state") or "active_play")
        keep_decision = str(raw.get("keep_decision") or "keep_active")

        segments.append(
            TimelineSegment(
                segment_id=segment_id,
                job_id=job_id,
                candidate_id=block_id or None,
                start_time=round(start, 3),
                end_time=round(end, 3),
                segment_role=state,
                selection_score=1.0,
                notes=[
                    "render_source:g8_timeline_plan",
                    f"g8_plan:{path.as_posix()}",
                    f"g8_block:{block_id}",
                    f"g8_keep_decision:{keep_decision}",
                ],
                source="g8_timeline_plan",
            )
        )

    if planned_duration <= 0.0:
        planned_duration = round(sum(segment.duration for segment in segments), 3)

    label = str(data.get("label") or path.stem)
    plan_id = str(data.get("plan_id") or label)

    timeline = EditTimeline(
        timeline_id=f"render_from_g8_{plan_id}",
        job_id=job_id,
        target_duration=round(planned_duration, 3),
        selected_segments=segments,
        hook_segment_id=segments[0].segment_id if segments else None,
        peak_segment_ids=[],
        payoff_segment_id=segments[-1].segment_id if segments else None,
        timeline_score=1.0,
        timeline_notes=[
            "render_source:g8_timeline_plan",
            f"g8_plan_path:{path.as_posix()}",
            f"g8_label:{label}",
            f"g8_status:{data.get('status')}",
            f"g8_anti_overcut_fail_count:{((data.get('anti_overcut_audit') or {}).get('fail_count'))}",
        ],
    )

    return timeline


def compare_timeline_to_g8_plan(
    *,
    timeline: EditTimeline,
    plan_data: dict[str, Any],
    tolerance_seconds: float = 0.0005,
) -> dict[str, Any]:
    plan_segments = plan_data.get("timeline_segments") or []
    timeline_segments = timeline.selected_segments

    deviations: list[dict[str, Any]] = []
    matched = 0

    for index, raw in enumerate(plan_segments):
        if index >= len(timeline_segments):
            deviations.append({
                "index": index,
                "reason": "missing_render_segment",
                "plan": raw,
                "render": None,
            })
            continue

        render_seg = timeline_segments[index]
        plan_start = round(float(raw.get("start_seconds")), 3)
        plan_end = round(float(raw.get("end_seconds")), 3)
        render_start = round(float(render_seg.start_time), 3)
        render_end = round(float(render_seg.end_time), 3)

        ok = (
            abs(plan_start - render_start) <= tolerance_seconds
            and abs(plan_end - render_end) <= tolerance_seconds
        )

        if ok:
            matched += 1
            continue

        deviations.append({
            "index": index,
            "reason": "time_range_mismatch",
            "plan_segment_id": raw.get("segment_id"),
            "render_segment_id": render_seg.segment_id,
            "plan_start": plan_start,
            "plan_end": plan_end,
            "render_start": render_start,
            "render_end": render_end,
        })

    if len(timeline_segments) > len(plan_segments):
        for index in range(len(plan_segments), len(timeline_segments)):
            render_seg = timeline_segments[index]
            deviations.append({
                "index": index,
                "reason": "extra_render_segment",
                "plan": None,
                "render_segment_id": render_seg.segment_id,
                "render_start": render_seg.start_time,
                "render_end": render_seg.end_time,
            })

    anti = plan_data.get("anti_overcut_audit") or {}
    anti_fail_count = int(anti.get("fail_count") or 0)

    return {
        "plan_segment_count": len(plan_segments),
        "render_segment_count": len(timeline_segments),
        "matched_segments": matched,
        "deviation_count": len(deviations),
        "deviations": deviations,
        "anti_overcut_fail_count": anti_fail_count,
        "anti_overcut_preserved": anti_fail_count == 0 and len(deviations) == 0,
    }
