from __future__ import annotations

import os

import pytest

from core.adaptive_silence_classifier import (
    classify_silence_detection_result,
    classify_silence_segment,
    classify_silence_segments,
)
from models.silence_classification import SilenceClassification, SilenceClassificationResult
from models.silence_detection import SilenceDetectionResult, SilenceSegment


def _make_segment(duration: float, start: float = 0.0) -> SilenceSegment:
    return SilenceSegment(
        start_seconds=start,
        end_seconds=start + duration,
        duration_seconds=duration,
    )


def _make_dict_segment(duration: float, start: float = 0.0) -> dict:
    return {
        "start_seconds": start,
        "end_seconds": start + duration,
        "duration_seconds": duration,
    }


# ─── Roundtrip ───────────────────────────────────────────────────────────────

def test_silence_classification_roundtrip():
    obj = SilenceClassification(
        start_seconds=1.0,
        end_seconds=1.5,
        duration_seconds=0.5,
        classification="sentence_gap",
        remove_candidate=True,
        confidence=0.75,
        reason="duration_within_sentence_gap_range",
        rules_applied=["duration_within_sentence_gap_range"],
        source_segment={"start_seconds": 1.0},
        context={"previous_energy_score": 0.3},
        warnings=["w1"],
        errors=[],
        metadata={"foo": "bar"},
    )
    restored = SilenceClassification.from_dict(obj.to_dict())
    assert restored.classification == "sentence_gap"
    assert restored.remove_candidate is True
    assert restored.confidence == 0.75
    assert restored.reason == "duration_within_sentence_gap_range"
    assert restored.rules_applied == ["duration_within_sentence_gap_range"]
    assert restored.warnings == ["w1"]
    assert restored.metadata == {"foo": "bar"}


def test_silence_classification_result_roundtrip():
    c = SilenceClassification(
        start_seconds=0.0,
        end_seconds=0.2,
        duration_seconds=0.2,
        classification="filler_pause",
        remove_candidate=True,
        confidence=0.85,
        reason="duration_under_filler_pause_limit",
    )
    result = SilenceClassificationResult(
        status="ok",
        classifications=[c],
        classification_count=1,
        remove_candidate_count=1,
        keep_candidate_count=0,
        counts_by_classification={"filler_pause": 1},
        warnings=[],
        errors=[],
        metadata={"x": 1},
    )
    restored = SilenceClassificationResult.from_dict(result.to_dict())
    assert restored.status == "ok"
    assert restored.classification_count == 1
    assert restored.remove_candidate_count == 1
    assert restored.keep_candidate_count == 0
    assert restored.counts_by_classification == {"filler_pause": 1}
    assert len(restored.classifications) == 1
    assert restored.classifications[0].classification == "filler_pause"
    assert restored.metadata == {"x": 1}


# ─── Classification cases ─────────────────────────────────────────────────────

def test_filler_pause_classification():
    seg = _make_segment(0.20)
    result = classify_silence_segment(seg)
    assert result.classification == "filler_pause"
    assert result.remove_candidate is True


def test_sentence_gap_classification():
    seg = _make_segment(0.45)
    result = classify_silence_segment(seg)
    assert result.classification == "sentence_gap"
    assert result.remove_candidate is True


def test_dramatic_pause_after_high_energy_is_kept():
    seg = _make_segment(1.20)
    ctx = {"previous_energy_score": 0.90}
    result = classify_silence_segment(seg, context=ctx)
    assert result.classification == "dramatic_pause"
    assert result.remove_candidate is False


def test_dramatic_pause_before_high_energy_is_kept():
    seg = _make_segment(1.00)
    ctx = {"next_is_peak": True}
    result = classify_silence_segment(seg, context=ctx)
    assert result.classification == "dramatic_pause"
    assert result.remove_candidate is False


def test_dead_air_without_energy_is_remove_candidate():
    seg = _make_segment(2.50)
    result = classify_silence_segment(seg, context={})
    assert result.classification == "dead_air"
    assert result.remove_candidate is True


def test_unknown_when_context_insufficient():
    seg = _make_segment(1.00)
    result = classify_silence_segment(seg, context={})
    assert result.classification == "unknown"
    assert result.remove_candidate is False


def test_invalid_negative_duration_does_not_crash():
    seg = _make_segment(-1.0)
    result = classify_silence_segment(seg)
    assert result.classification == "unknown"
    assert "invalid_duration" in result.errors


# ─── Profile overrides ────────────────────────────────────────────────────────

def test_profile_overrides_duration_thresholds():
    profile = {"audio": {"filler_pause_max_seconds": 0.50}}
    seg = _make_segment(0.45)
    result = classify_silence_segment(seg, profile=profile)
    assert result.classification == "filler_pause"


# ─── List classification ──────────────────────────────────────────────────────

def test_classify_silence_segments_counts_classes():
    segments = [
        _make_segment(0.20),
        _make_segment(0.45),
        _make_segment(2.50),
    ]
    result = classify_silence_segments(segments)
    assert result.classification_count == 3
    assert result.remove_candidate_count == 3
    assert result.keep_candidate_count == 0
    assert result.counts_by_classification.get("filler_pause", 0) == 1
    assert result.counts_by_classification.get("sentence_gap", 0) == 1
    assert result.counts_by_classification.get("dead_air", 0) == 1


# ─── Detection result integration ─────────────────────────────────────────────

def test_classify_silence_detection_result_from_object():
    detection = SilenceDetectionResult(
        source_path="fake.mp4",
        status="ok",
        segments=[
            _make_segment(0.20),
            _make_segment(0.45),
        ],
        segment_count=2,
    )
    result = classify_silence_detection_result(detection)
    assert result.classification_count == 2


def test_classify_silence_detection_result_from_dict():
    data = {
        "source_path": "fake.mp4",
        "status": "ok",
        "segments": [
            _make_dict_segment(0.20),
            _make_dict_segment(0.45),
        ],
    }
    result = classify_silence_detection_result(data)
    assert result.classification_count == 2


def test_empty_detection_result_is_ok():
    detection = SilenceDetectionResult(
        source_path="fake.mp4",
        status="ok",
        segments=[],
        segment_count=0,
    )
    result = classify_silence_detection_result(detection)
    assert result.status == "ok"
    assert result.classification_count == 0


# ─── File hygiene ─────────────────────────────────────────────────────────────

def test_classifier_files_have_no_bom_and_end_with_newline():
    base = os.path.join(os.path.dirname(__file__), "..")
    files = [
        os.path.join(base, "models", "silence_classification.py"),
        os.path.join(base, "core", "adaptive_silence_classifier.py"),
        os.path.join(base, "tests", "test_adaptive_silence_classifier_foundation_smoke.py"),
    ]
    for path in files:
        with open(path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
