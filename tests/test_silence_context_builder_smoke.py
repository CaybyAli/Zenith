from __future__ import annotations

import os

import pytest

from core.silence_context_builder import (
    build_silence_contexts,
    build_silence_contexts_from_detection_result,
    build_silence_segment_context,
)
from core.adaptive_silence_classifier import classify_silence_segment
from models.silence_context import SilenceContextBuildResult, SilenceSegmentContext
from models.silence_detection import SilenceDetectionResult, SilenceSegment


def _make_segment(start: float, end: float) -> SilenceSegment:
    return SilenceSegment(
        start_seconds=start,
        end_seconds=end,
        duration_seconds=end - start,
    )


def test_silence_segment_context_roundtrip():
    ctx = SilenceSegmentContext(
        start_seconds=10.0,
        end_seconds=11.0,
        duration_seconds=1.0,
        previous_energy_score=0.8,
        next_energy_score=0.6,
        previous_content_value=0.7,
        next_content_value=0.5,
        previous_is_peak=True,
        next_is_peak=False,
        is_after_high_energy=True,
        is_before_high_energy=False,
        previous_has_speech=True,
        next_has_speech=False,
        warnings=["w1"],
        errors=[],
        metadata={"k": "v"},
    )
    d = ctx.to_dict()
    restored = SilenceSegmentContext.from_dict(d)
    assert restored.start_seconds == 10.0
    assert restored.end_seconds == 11.0
    assert restored.duration_seconds == 1.0
    assert restored.previous_energy_score == 0.8
    assert restored.next_energy_score == 0.6
    assert restored.previous_content_value == 0.7
    assert restored.next_content_value == 0.5
    assert restored.previous_is_peak is True
    assert restored.next_is_peak is False
    assert restored.is_after_high_energy is True
    assert restored.is_before_high_energy is False
    assert restored.previous_has_speech is True
    assert restored.next_has_speech is False
    assert restored.warnings == ["w1"]
    assert restored.metadata == {"k": "v"}


def test_silence_context_build_result_roundtrip():
    ctx = SilenceSegmentContext(start_seconds=1.0, end_seconds=2.0, duration_seconds=1.0)
    result = SilenceContextBuildResult(
        status="ok",
        contexts=[ctx],
        context_count=1,
        high_energy_context_count=0,
        warnings=[],
        errors=[],
        metadata={"x": 1},
    )
    d = result.to_dict()
    restored = SilenceContextBuildResult.from_dict(d)
    assert restored.status == "ok"
    assert restored.context_count == 1
    assert len(restored.contexts) == 1
    assert restored.high_energy_context_count == 0
    assert restored.metadata == {"x": 1}


def test_build_context_detects_previous_high_energy():
    seg = _make_segment(10.0, 10.5)
    energy_timeline = [{"time_seconds": 9.5, "energy_score": 0.9}]
    ctx = build_silence_segment_context(seg, energy_timeline=energy_timeline)
    assert ctx.previous_energy_score == pytest.approx(0.9)
    assert ctx.is_after_high_energy is True


def test_build_context_detects_next_high_energy():
    seg = _make_segment(10.0, 10.5)
    energy_timeline = [{"time_seconds": 10.8, "energy_score": 0.85}]
    ctx = build_silence_segment_context(seg, energy_timeline=energy_timeline)
    assert ctx.next_energy_score == pytest.approx(0.85)
    assert ctx.is_before_high_energy is True


def test_build_context_uses_explicit_peak_flags():
    seg = _make_segment(10.0, 10.5)
    energy_timeline = [{"time_seconds": 9.8, "energy_score": 0.3, "is_peak": True}]
    ctx = build_silence_segment_context(seg, energy_timeline=energy_timeline)
    assert ctx.previous_is_peak is True
    assert ctx.is_after_high_energy is True


def test_build_context_content_values():
    seg = _make_segment(10.0, 10.5)
    content_timeline = [
        {"time_seconds": 9.8, "content_value": 0.7},
        {"time_seconds": 11.0, "content_value": 0.8},
    ]
    ctx = build_silence_segment_context(seg, content_timeline=content_timeline)
    assert ctx.previous_content_value == pytest.approx(0.7)
    assert ctx.next_content_value == pytest.approx(0.8)


def test_build_context_speech_overlap():
    seg = _make_segment(10.0, 10.5)
    speech_segments = [
        {"start_seconds": 9.0, "end_seconds": 10.0},
    ]
    ctx = build_silence_segment_context(seg, speech_segments=speech_segments)
    assert ctx.previous_has_speech is True
    assert ctx.next_has_speech is False


def test_build_contexts_returns_one_context_per_segment():
    segments = [_make_segment(i * 5.0, i * 5.0 + 1.0) for i in range(3)]
    result = build_silence_contexts(segments)
    assert result.context_count == 3
    assert len(result.contexts) == 3


def test_build_contexts_counts_high_energy_contexts():
    seg1 = _make_segment(10.0, 10.5)
    seg2 = _make_segment(20.0, 20.5)
    energy_timeline = [{"time_seconds": 9.5, "energy_score": 0.9}]
    result = build_silence_contexts([seg1, seg2], energy_timeline=energy_timeline)
    assert result.high_energy_context_count == 1


def test_build_contexts_from_detection_result_object():
    detection = SilenceDetectionResult(
        source_path="fake.mp4",
        status="ok",
        segments=[_make_segment(5.0, 6.0), _make_segment(10.0, 11.0)],
        segment_count=2,
    )
    result = build_silence_contexts_from_detection_result(detection)
    assert result.context_count == 2
    assert len(result.contexts) == 2


def test_build_contexts_from_detection_result_dict():
    d = {
        "source_path": "fake.mp4",
        "status": "ok",
        "segments": [
            {"start_seconds": 5.0, "end_seconds": 6.0, "duration_seconds": 1.0},
            {"start_seconds": 10.0, "end_seconds": 11.0, "duration_seconds": 1.0},
        ],
    }
    result = build_silence_contexts_from_detection_result(d)
    assert result.context_count == 2


def test_empty_detection_result_is_ok():
    detection = SilenceDetectionResult(
        source_path="fake.mp4",
        status="ok",
        segments=[],
        segment_count=0,
    )
    result = build_silence_contexts_from_detection_result(detection)
    assert result.status == "ok"
    assert result.context_count == 0


def test_bad_timeline_items_do_not_crash():
    seg = _make_segment(10.0, 10.5)
    bad_timeline = [
        {},
        {"time_seconds": "bad", "energy_score": "bad"},
    ]
    result = build_silence_segment_context(seg, energy_timeline=bad_timeline)
    assert isinstance(result, SilenceSegmentContext)


def test_invalid_segments_input_failed():
    result = build_silence_contexts("not-a-list")
    assert result.status == "failed"
    assert "invalid_segments_input" in result.errors


def test_context_dicts_are_usable_by_adaptive_classifier():
    seg = _make_segment(10.0, 11.2)
    energy_timeline = [{"time_seconds": 9.5, "energy_score": 0.9}]
    ctx = build_silence_segment_context(seg, energy_timeline=energy_timeline)
    classification = classify_silence_segment(seg, context=ctx.to_dict())
    assert classification.classification == "dramatic_pause"
    assert classification.remove_candidate is False


def test_silence_context_builder_files_have_no_bom_and_end_with_newline():
    files = [
        os.path.join(os.path.dirname(__file__), "..", "models", "silence_context.py"),
        os.path.join(os.path.dirname(__file__), "..", "core", "silence_context_builder.py"),
        os.path.join(os.path.dirname(__file__), "test_silence_context_builder_smoke.py"),
    ]
    for path in files:
        abs_path = os.path.abspath(path)
        with open(abs_path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {abs_path}"
        assert raw.endswith(b"\n"), f"File does not end with newline: {abs_path}"
