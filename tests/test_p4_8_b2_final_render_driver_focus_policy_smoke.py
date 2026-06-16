from __future__ import annotations

from types import SimpleNamespace

from core.final_render_driver import FinalRenderDriver
from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment


def _segment(segment_id: str = "seg_focus") -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="job_focus_policy",
        candidate_id=None,
        start_time=10.0,
        end_time=20.0,
        segment_role="peak",
        selection_score=1.0,
    )


def _plan(segment_id: str, layout_kind: str = "balanced_split") -> ReframePlan:
    return ReframePlan(
        plan_id="reframe_focus_policy",
        job_id="job_focus_policy",
        timeline_id="timeline_focus_policy",
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        instructions=[
            FramingInstruction(
                instruction_id="frame_focus_policy",
                job_id="job_focus_policy",
                timeline_id="timeline_focus_policy",
                segment_id=segment_id,
                focus_kind="balanced",
                layout_kind=layout_kind,
                source_aspect_ratio="32:9",
                target_aspect_ratio="16:9",
                crop_window={"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0},
            )
        ],
        plan_score=1.0,
    )


def test_focus_decision_gameplay_overrides_reframe_layout_for_32x9() -> None:
    driver = FinalRenderDriver()
    segment = _segment()
    job = SimpleNamespace(
        job_id="job_focus_policy",
        focus_decisions=[
            {
                "timestamp": 12.0,
                "focus_target": "gameplay",
                "gameplay_zoom": 1.3,
                "facecam_opacity": 0.3,
                "confidence": 0.9,
                "reasoning": "friend_keyword_test",
            }
        ],
    )

    policy = driver._resolve_focus_render_policy(
        segment=segment,
        job=job,
        reframe_plan=_plan(segment.segment_id, "balanced_split"),
    )
    fc, label = driver._build_filter_complex(
        segment=segment,
        reframe_plan=_plan(segment.segment_id, "balanced_split"),
        dynamic_edit_plan=None,
        audio_peaks=[],
        src_w=3840,
        src_h=1080,
        focus_policy=policy,
    )

    assert label == "[out]"
    assert policy["policy_source"] == "focus_decision"
    assert policy["focus_target"] == "gameplay"
    assert policy["layout_kind"] == "gameplay_crop"
    assert "crop=1920:1080:1920:0" in fc
    assert "scale=w='1920*(if(lt(t\\,0.12)" in fc
    assert ":h='1080*(if(lt(t\\,0.12)" in fc
    assert "eval=frame" in fc
    assert "crop=1920:1080:x='2*floor(1920*((if(lt(t\\,0.12)" in fc
    assert ":y='2*floor(1080*((if(lt(t\\,0.12)" in fc
    assert "overlay=" not in fc


def test_focus_decision_facecam_overrides_reframe_layout_for_32x9() -> None:
    driver = FinalRenderDriver()
    segment = _segment()
    job = SimpleNamespace(
        job_id="job_focus_policy",
        focus_decisions=[
            {
                "timestamp": 13.0,
                "focus_target": "facecam",
                "facecam_zoom": 1.8,
                "confidence": 0.95,
                "reasoning": "ali_voice_intensity_test",
            }
        ],
    )

    policy = driver._resolve_focus_render_policy(
        segment=segment,
        job=job,
        reframe_plan=_plan(segment.segment_id, "gameplay_crop"),
    )
    fc, label = driver._build_filter_complex(
        segment=segment,
        reframe_plan=_plan(segment.segment_id, "gameplay_crop"),
        dynamic_edit_plan=None,
        audio_peaks=[],
        src_w=3840,
        src_h=1080,
        focus_policy=policy,
    )

    assert label == "[out]"
    assert policy["policy_source"] == "focus_decision"
    assert policy["focus_target"] == "facecam"
    assert policy["layout_kind"] == "facecam_emphasis"
    assert "crop=1920:1080:1920:0" in fc
    assert "[gp][fc]overlay=" in fc
    assert "overlay=" in fc


def test_focus_decision_balanced_keeps_pip_layout_for_32x9() -> None:
    driver = FinalRenderDriver()
    segment = _segment()
    job = SimpleNamespace(
        job_id="job_focus_policy",
        focus_decisions=[
            {
                "timestamp": 14.0,
                "focus_target": "balanced",
                "confidence": 0.8,
                "reasoning": "friend_speaking_no_keyword",
            }
        ],
    )

    policy = driver._resolve_focus_render_policy(
        segment=segment,
        job=job,
        reframe_plan=_plan(segment.segment_id, "gameplay_crop"),
    )
    fc, label = driver._build_filter_complex(
        segment=segment,
        reframe_plan=_plan(segment.segment_id, "gameplay_crop"),
        dynamic_edit_plan=None,
        audio_peaks=[],
        src_w=3840,
        src_h=1080,
        focus_policy=policy,
    )

    assert label == "[out]"
    assert policy["policy_source"] == "focus_decision"
    assert policy["focus_target"] == "balanced"
    assert policy["layout_kind"] == "balanced_split"
    assert "overlay=" in fc
    assert "crop=1920:1080:1920:0" in fc


def test_focus_policy_records_render_context_counts() -> None:
    driver = FinalRenderDriver()
    segments = [
        _segment("seg_gameplay"),
        _segment("seg_facecam"),
        _segment("seg_balanced"),
    ]
    segments[0].start_time = 10.0
    segments[0].end_time = 20.0
    segments[1].start_time = 20.0
    segments[1].end_time = 30.0
    segments[2].start_time = 30.0
    segments[2].end_time = 40.0

    job = SimpleNamespace(
        job_id="job_focus_policy_context",
        focus_decisions=[
            {"timestamp": 12.0, "focus_target": "gameplay", "confidence": 0.9},
            {"timestamp": 22.0, "focus_target": "facecam", "confidence": 0.9},
            {"timestamp": 32.0, "focus_target": "balanced", "confidence": 0.9},
        ],
    )

    layout_counts: dict[str, int] = {}
    records = []

    for segment in segments:
        policy = driver._resolve_focus_render_policy(
            segment=segment,
            job=job,
            reframe_plan=_plan(segment.segment_id, "balanced_split"),
        )
        records.append(policy)
        layout = str(policy.get("layout_kind") or "unknown")
        layout_counts[layout] = layout_counts.get(layout, 0) + 1

    assert any(item["policy_source"] == "focus_decision" for item in records)
    assert layout_counts == {
        "balanced_split": 1,
        "facecam_emphasis": 1,
        "gameplay_crop": 1,
    }
    assert [item["focus_target"] for item in records] == [
        "gameplay",
        "facecam",
        "balanced",
    ]

