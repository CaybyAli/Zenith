from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import pytest

from core.silence_classifier_runner import (
    build_silence_classifier_run_report,
    run_silence_classifier_for_job,
)
from models.silence_classifier_run import SilenceClassifierRunReport
from models.silence_detection import SilenceDetectionResult, SilenceSegment


def _seg_dict(duration: float, start: float = 0.0) -> dict[str, Any]:
    return {
        "start_seconds": start,
        "end_seconds": start + duration,
        "duration_seconds": duration,
    }


def _seg_obj(duration: float, start: float = 0.0) -> SilenceSegment:
    return SilenceSegment(
        start_seconds=start,
        end_seconds=start + duration,
        duration_seconds=duration,
    )


def _detection_dict(durations: list[float]) -> dict[str, Any]:
    return {
        "status": "ok",
        "source_path": "/fake/audio.wav",
        "segments": [_seg_dict(d, i * 5.0) for i, d in enumerate(durations)],
    }


# ─── 1. Roundtrip ────────────────────────────────────────────────────────────

def test_silence_classifier_run_report_roundtrip():
    report = SilenceClassifierRunReport(
        status="ok",
        detection_status="ok",
        classification_status="ok",
        classification_result={"status": "ok"},
        classifications=[{"classification": "filler_pause"}],
        classification_count=1,
        remove_candidate_count=1,
        keep_candidate_count=0,
        counts_by_classification={"filler_pause": 1},
        warnings=["w1"],
        errors=[],
        recommendation="use_classification",
        metadata={"test": True},
    )
    restored = SilenceClassifierRunReport.from_dict(report.to_dict())
    assert restored.status == "ok"
    assert restored.classification_count == 1
    assert restored.remove_candidate_count == 1
    assert restored.counts_by_classification == {"filler_pause": 1}
    assert restored.recommendation == "use_classification"
    assert restored.warnings == ["w1"]
    assert restored.metadata == {"test": True}


# ─── 2. Detection dict with segments ─────────────────────────────────────────

def test_runner_classifies_detection_result_dict():
    detection = _detection_dict([0.20, 0.45, 2.50])
    report = build_silence_classifier_run_report(detection)
    assert report.status == "ok"
    assert report.classification_count == 3
    assert report.remove_candidate_count == 3
    assert "filler_pause" in report.counts_by_classification
    assert "sentence_gap" in report.counts_by_classification
    assert "dead_air" in report.counts_by_classification
    assert report.recommendation == "use_classification"


# ─── 3. Detection result object ──────────────────────────────────────────────

def test_runner_classifies_detection_result_object():
    result_obj = SilenceDetectionResult(
        source_path="/fake/audio.wav",
        status="ok",
        segments=[_seg_obj(0.25, 0.0), _seg_obj(0.50, 5.0)],
        segment_count=2,
    )
    report = build_silence_classifier_run_report(result_obj)
    assert report.classification_count == 2
    assert report.status in ("ok", "completed_with_warnings")


# ─── 4. Contexts trigger dramatic_pause ──────────────────────────────────────

def test_runner_uses_contexts_for_dramatic_pause():
    detection = _detection_dict([1.20])
    contexts = [{"previous_energy_score": 0.9}]
    report = build_silence_classifier_run_report(detection, contexts=contexts)
    assert report.classification_count == 1
    assert report.counts_by_classification.get("dramatic_pause", 0) == 1
    assert report.remove_candidate_count == 0
    assert report.keep_candidate_count == 1


# ─── 5. Empty segments → skipped ─────────────────────────────────────────────

def test_runner_skips_empty_detection_result():
    detection = {"status": "ok", "source_path": "/fake/audio.wav", "segments": []}
    report = build_silence_classifier_run_report(detection)
    assert report.status == "skipped_no_silence_segments"
    assert report.recommendation == "no_silence_to_classify"
    assert report.classification_count == 0


# ─── 6. Missing detection result → failed ────────────────────────────────────

def test_runner_fails_missing_detection_result():
    report = build_silence_classifier_run_report(None)
    assert report.status == "failed"
    assert any("missing_detection_result" in e for e in report.errors)


# ─── 7. Bad detection result → no crash ──────────────────────────────────────

def test_runner_handles_bad_detection_result_without_crash():
    for bad in [42, "not_a_result", object(), {"segments": "NOT_A_LIST"}]:
        report = build_silence_classifier_run_report(bad)
        assert report is not None
        assert report.status in ("failed", "skipped_no_silence_segments")


# ─── 8. Job reads silence_detection_result ───────────────────────────────────

def test_run_silence_classifier_for_job_reads_job_silence_detection_result():
    job = SimpleNamespace(
        silence_detection_result=_detection_dict([0.20, 0.50]),
        silence_detection_report={},
        profile_metadata={},
    )
    report = run_silence_classifier_for_job(job)
    assert report.classification_count > 0


# ─── 9. Job fallback to silence_detection_report.detection_result ─────────────

def test_run_silence_classifier_for_job_falls_back_to_report_detection_result():
    job = SimpleNamespace(
        silence_detection_result={},
        silence_detection_report={
            "detection_result": _detection_dict([0.25, 0.55]),
        },
        profile_metadata={},
    )
    report = run_silence_classifier_for_job(job)
    assert report.classification_count > 0


# ─── 10. Job profile_metadata is used ────────────────────────────────────────

def test_run_silence_classifier_for_job_uses_job_profile_metadata():
    job = SimpleNamespace(
        silence_detection_result=_detection_dict([0.45]),
        silence_detection_report={},
        profile_metadata={"audio": {"filler_pause_max_seconds": 0.50}},
    )
    report = run_silence_classifier_for_job(job)
    assert report.classification_count == 1
    assert report.counts_by_classification.get("filler_pause", 0) == 1


# ─── 11. Empty job → safe ────────────────────────────────────────────────────

def test_run_silence_classifier_for_empty_job_is_safe():
    job = SimpleNamespace()
    report = run_silence_classifier_for_job(job)
    assert report is not None
    assert report.status == "failed"
    assert any("missing_detection_result" in e for e in report.errors)


# ─── 12. BOM and newline hygiene ─────────────────────────────────────────────

def test_silence_classifier_runner_files_have_no_bom_and_end_with_newline():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [
        os.path.join(base, "models", "silence_classifier_run.py"),
        os.path.join(base, "core", "silence_classifier_runner.py"),
        os.path.join(base, "tests", "test_silence_classifier_runner_smoke.py"),
    ]
    for path in files:
        with open(path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
