from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

from core.silence_classifier_runner import (
    build_silence_classifier_run_report,
    run_silence_classifier_for_job,
)
from models.silence_classifier_run import SilenceClassifierRunReport
from models.silence_detection import SilenceDetectionResult, SilenceSegment


def _seg(start: float, duration: float) -> dict[str, Any]:
    return {
        "start_seconds": start,
        "end_seconds": start + duration,
        "duration_seconds": duration,
    }


def _detection(segments: list[dict[str, Any]]) -> dict[str, Any]:
    return {"status": "ok", "source_path": "/fake/audio.wav", "segments": segments}


# ─── 1. Roundtrip preserves context fields ───────────────────────────────────

def test_report_roundtrip_preserves_context_fields():
    report = SilenceClassifierRunReport(
        status="ok",
        context_build_status="ok",
        context_build_result={"status": "ok", "context_count": 1},
        contexts=[{"start_seconds": 5.0, "previous_energy_score": 0.9}],
        context_count=1,
        high_energy_context_count=1,
    )
    d = report.to_dict()
    restored = SilenceClassifierRunReport.from_dict(d)
    assert restored.context_build_status == "ok"
    assert restored.context_count == 1
    assert restored.high_energy_context_count == 1
    assert len(restored.contexts) == 1
    assert restored.contexts[0].get("previous_energy_score") == 0.9
    assert restored.context_build_result.get("status") == "ok"


# ─── 2. Auto-builds contexts from energy_timeline ────────────────────────────

def test_runner_auto_builds_contexts_from_energy_timeline():
    detection = _detection([_seg(5.0, 1.2)])
    energy_timeline = [{"time_seconds": 4.5, "energy_score": 0.9}]
    report = build_silence_classifier_run_report(detection, energy_timeline=energy_timeline)
    assert report.status == "ok"
    assert report.context_build_status == "ok"
    assert report.context_count == 1
    assert report.high_energy_context_count == 1
    assert report.counts_by_classification.get("dramatic_pause", 0) == 1
    assert report.remove_candidate_count == 0
    assert report.keep_candidate_count == 1


# ─── 3. Provided contexts take priority over auto-builder ─────────────────────

def test_runner_uses_provided_contexts_over_auto_builder():
    detection = _detection([_seg(5.0, 1.2)])
    provided = [{"previous_energy_score": 0.9}]
    # energy_timeline is empty — auto-builder would produce no high-energy context
    report = build_silence_classifier_run_report(
        detection, contexts=provided, energy_timeline=[]
    )
    assert report.context_build_status == "provided"
    assert report.counts_by_classification.get("dramatic_pause", 0) == 1


# ─── 4. auto_build_contexts=False disables context building ──────────────────

def test_runner_can_disable_auto_context_building():
    detection = _detection([_seg(5.0, 1.2)])
    energy_timeline = [{"time_seconds": 4.5, "energy_score": 0.9}]
    report = build_silence_classifier_run_report(
        detection, energy_timeline=energy_timeline, auto_build_contexts=False
    )
    assert report.context_build_status == "disabled"
    assert len(report.contexts) == 0
    assert report.context_count == 0
    # No high-energy context → duration 1.2 (in dramatic range) → "unknown"
    assert report.counts_by_classification.get("dramatic_pause", 0) == 0
    assert report.counts_by_classification.get("unknown", 0) == 1


# ─── 5. Empty detection result → skipped, no crash ───────────────────────────

def test_runner_context_builder_handles_empty_detection_result():
    detection = SilenceDetectionResult(
        source_path="fake.mp4", status="ok", segments=[], segment_count=0
    )
    report = build_silence_classifier_run_report(detection)
    assert report.status == "skipped_no_silence_segments"
    assert report.context_count == 0


# ─── 6. Bad energy timeline → no crash ───────────────────────────────────────

def test_runner_survives_bad_energy_timeline():
    detection = _detection([_seg(5.0, 1.2)])
    bad_timeline: list[Any] = [{}, {"time_seconds": "bad", "energy_score": "bad"}]
    report = build_silence_classifier_run_report(detection, energy_timeline=bad_timeline)
    assert report is not None
    assert report.status in ("ok", "completed_with_warnings")
    assert report.classification_count == 1


# ─── 7. Job provides energy_timeline ─────────────────────────────────────────

def test_run_for_job_reads_energy_timeline_from_job():
    job = SimpleNamespace(
        silence_detection_result=_detection([_seg(5.0, 1.2)]),
        energy_timeline=[{"time_seconds": 4.5, "energy_score": 0.9}],
        profile_metadata={},
    )
    report = run_silence_classifier_for_job(job)
    assert report.counts_by_classification.get("dramatic_pause", 0) == 1
    assert report.high_energy_context_count == 1


# ─── 8. Direct energy_timeline overrides job.energy_timeline ─────────────────

def test_run_for_job_uses_direct_energy_timeline_over_job_energy():
    job = SimpleNamespace(
        silence_detection_result=_detection([_seg(5.0, 1.2)]),
        energy_timeline=[{"time_seconds": 4.5, "energy_score": 0.2}],
        profile_metadata={},
    )
    direct_energy = [{"time_seconds": 4.5, "energy_score": 0.9}]
    report = run_silence_classifier_for_job(job, energy_timeline=direct_energy)
    assert report.counts_by_classification.get("dramatic_pause", 0) == 1


# ─── 9. Job provides speech_segments ─────────────────────────────────────────

def test_run_for_job_reads_speech_segments_from_job():
    job = SimpleNamespace(
        silence_detection_result=_detection([_seg(5.0, 1.2)]),
        speech_segments=[{"start_seconds": 4.0, "end_seconds": 5.0}],
        profile_metadata={},
    )
    report = run_silence_classifier_for_job(job)
    assert report.context_count == 1
    assert len(report.contexts) == 1
    ctx = report.contexts[0]
    assert ctx.get("previous_has_speech") is True
    assert ctx.get("next_has_speech") is False


# ─── 10. BOM and newline hygiene ─────────────────────────────────────────────

def test_context_wiring_files_have_no_bom_and_end_with_newline():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [
        os.path.join(base, "core", "silence_classifier_runner.py"),
        os.path.join(base, "models", "silence_classifier_run.py"),
        os.path.join(base, "tests", "test_silence_classifier_context_wiring_smoke.py"),
    ]
    for path in files:
        with open(path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
