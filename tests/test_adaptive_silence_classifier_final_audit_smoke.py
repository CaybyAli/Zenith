from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from core.adaptive_silence_classifier import classify_silence_segment, classify_silence_segments
from core.silence_classifier_runner import (
    build_silence_classifier_run_report,
    run_silence_classifier_for_job,
)
from core.silence_context_builder import (
    build_silence_contexts,
    build_silence_segment_context,
)
from models.silence_classification import SilenceClassification, SilenceClassificationResult
from models.silence_classifier_run import SilenceClassifierRunReport
from models.silence_context import SilenceContextBuildResult, SilenceSegmentContext
from models.silence_detection import SilenceDetectionResult, SilenceSegment

REPO_ROOT = Path(__file__).resolve().parent.parent


def _seg(start: float, duration: float) -> SilenceSegment:
    return SilenceSegment(
        start_seconds=start,
        end_seconds=start + duration,
        duration_seconds=duration,
    )


def _detection(segments: list[SilenceSegment]) -> SilenceDetectionResult:
    return SilenceDetectionResult(
        source_path="fake.mp4",
        status="ok",
        segments=segments,
        segment_count=len(segments),
    )


# ─── Test 1: All models roundtrip ────────────────────────────────────────────

def test_2b07_models_roundtrip() -> None:
    sc = SilenceClassification(
        start_seconds=1.0,
        end_seconds=2.0,
        duration_seconds=1.0,
        classification="dramatic_pause",
        remove_candidate=False,
        confidence=0.80,
        reason="high_energy_context",
        rules_applied=["high_energy_context_suggests_dramatic_pause"],
        context={"previous_energy_score": 0.9},
        warnings=["w1"],
        metadata={"k": "v"},
    )
    restored_sc = SilenceClassification.from_dict(sc.to_dict())
    assert restored_sc.classification == "dramatic_pause"
    assert restored_sc.remove_candidate is False
    assert restored_sc.context.get("previous_energy_score") == 0.9
    assert restored_sc.warnings == ["w1"]

    scr = SilenceClassificationResult(
        status="ok",
        classifications=[sc],
        classification_count=1,
        remove_candidate_count=0,
        keep_candidate_count=1,
        counts_by_classification={"dramatic_pause": 1},
    )
    restored_scr = SilenceClassificationResult.from_dict(scr.to_dict())
    assert restored_scr.status == "ok"
    assert restored_scr.classification_count == 1
    assert len(restored_scr.classifications) == 1

    report = SilenceClassifierRunReport(
        status="ok",
        context_build_status="ok",
        context_build_result={"context_count": 1},
        contexts=[{"previous_energy_score": 0.9}],
        context_count=1,
        high_energy_context_count=1,
        classification_count=1,
        keep_candidate_count=1,
        counts_by_classification={"dramatic_pause": 1},
    )
    restored_report = SilenceClassifierRunReport.from_dict(report.to_dict())
    assert restored_report.context_build_status == "ok"
    assert restored_report.context_count == 1
    assert restored_report.high_energy_context_count == 1
    assert len(restored_report.contexts) == 1

    ctx = SilenceSegmentContext(
        start_seconds=5.0,
        end_seconds=6.2,
        duration_seconds=1.2,
        previous_energy_score=0.9,
        previous_is_peak=True,
        is_after_high_energy=True,
        previous_has_speech=True,
        next_has_speech=False,
    )
    restored_ctx = SilenceSegmentContext.from_dict(ctx.to_dict())
    assert restored_ctx.previous_energy_score == 0.9
    assert restored_ctx.previous_is_peak is True
    assert restored_ctx.is_after_high_energy is True
    assert restored_ctx.previous_has_speech is True

    cbr = SilenceContextBuildResult(
        status="ok",
        contexts=[ctx],
        context_count=1,
        high_energy_context_count=1,
    )
    restored_cbr = SilenceContextBuildResult.from_dict(cbr.to_dict())
    assert restored_cbr.status == "ok"
    assert restored_cbr.context_count == 1
    assert restored_cbr.high_energy_context_count == 1
    assert len(restored_cbr.contexts) == 1


# ─── Test 2: Classifier core rules ───────────────────────────────────────────

def test_2b07_classifier_core_rules() -> None:
    # filler_pause
    r = classify_silence_segment(_seg(0.0, 0.20))
    assert r.classification == "filler_pause"
    assert r.remove_candidate is True

    # sentence_gap
    r = classify_silence_segment(_seg(5.0, 0.45))
    assert r.classification == "sentence_gap"
    assert r.remove_candidate is True

    # dramatic_pause with high energy context
    r = classify_silence_segment(_seg(10.0, 1.20), context={"previous_energy_score": 0.90})
    assert r.classification == "dramatic_pause"
    assert r.remove_candidate is False

    # dead_air without context
    r = classify_silence_segment(_seg(20.0, 2.50))
    assert r.classification == "dead_air"
    assert r.remove_candidate is True

    # unknown without context (in dramatic range)
    r = classify_silence_segment(_seg(30.0, 1.20))
    assert r.classification == "unknown"
    assert r.remove_candidate is False

    # negative duration → invalid_duration
    bad_seg = {"start_seconds": 5.0, "end_seconds": 4.0, "duration_seconds": -1.0}
    r = classify_silence_segment(bad_seg)
    assert r.classification == "unknown"
    assert "invalid_duration" in r.errors


# ─── Test 3: Context builder contract ────────────────────────────────────────

def test_2b07_context_builder_contract() -> None:
    seg = _seg(10.0, 1.2)

    # previous high energy
    ctx = build_silence_segment_context(
        seg, energy_timeline=[{"time_seconds": 9.5, "energy_score": 0.9}]
    )
    assert ctx.previous_energy_score == 0.9
    assert ctx.is_after_high_energy is True

    # next high energy
    ctx = build_silence_segment_context(
        seg, energy_timeline=[{"time_seconds": 11.5, "energy_score": 0.85}]
    )
    assert ctx.next_energy_score == 0.85
    assert ctx.is_before_high_energy is True

    # explicit is_peak flag (low energy score, but peak=True)
    ctx = build_silence_segment_context(
        seg, energy_timeline=[{"time_seconds": 9.8, "energy_score": 0.3, "is_peak": True}]
    )
    assert ctx.previous_is_peak is True
    assert ctx.is_after_high_energy is True

    # content values
    ctx = build_silence_segment_context(
        seg,
        content_timeline=[
            {"time_seconds": 9.8, "content_value": 0.7},
            {"time_seconds": 11.5, "content_value": 0.8},
        ],
    )
    assert ctx.previous_content_value == 0.7
    assert ctx.next_content_value == 0.8

    # speech overlap
    ctx = build_silence_segment_context(
        seg,
        speech_segments=[{"start_seconds": 9.0, "end_seconds": 10.0}],
    )
    assert ctx.previous_has_speech is True
    assert ctx.next_has_speech is False

    # context dict is usable by the adaptive classifier
    ctx_high = build_silence_segment_context(
        seg, energy_timeline=[{"time_seconds": 9.5, "energy_score": 0.9}]
    )
    r = classify_silence_segment(seg, context=ctx_high.to_dict())
    assert r.classification == "dramatic_pause"
    assert r.remove_candidate is False


# ─── Test 4: Runner + context wiring ─────────────────────────────────────────

def test_2b07_runner_context_wiring_contract() -> None:
    detection = {
        "status": "ok",
        "source_path": "/fake/audio.wav",
        "segments": [
            {"start_seconds": 5.0, "end_seconds": 6.2, "duration_seconds": 1.2}
        ],
    }
    energy = [{"time_seconds": 4.5, "energy_score": 0.9}]

    # auto-build contexts from energy_timeline
    report = build_silence_classifier_run_report(detection, energy_timeline=energy)
    assert report.status == "ok"
    assert report.context_build_status == "ok"
    assert report.context_count == 1
    assert report.high_energy_context_count == 1
    assert report.counts_by_classification.get("dramatic_pause", 0) == 1

    # provided contexts take priority (empty energy won't override provided)
    provided = [{"previous_energy_score": 0.9}]
    report = build_silence_classifier_run_report(
        detection, contexts=provided, energy_timeline=[]
    )
    assert report.context_build_status == "provided"
    assert report.counts_by_classification.get("dramatic_pause", 0) == 1

    # auto_build_contexts=False → unknown (no context in dramatic range)
    report = build_silence_classifier_run_report(
        detection, energy_timeline=energy, auto_build_contexts=False
    )
    assert report.context_build_status == "disabled"
    assert report.counts_by_classification.get("dramatic_pause", 0) == 0
    assert report.counts_by_classification.get("unknown", 0) == 1


# ─── Test 5: Runner failure modes are safe ───────────────────────────────────

def test_2b07_runner_failure_modes_are_safe() -> None:
    # None detection result
    report = build_silence_classifier_run_report(None)
    assert report.status == "failed"
    assert any("missing_detection_result" in e for e in report.errors)

    # empty segments
    empty = {"status": "ok", "source_path": "/fake/audio.wav", "segments": []}
    report = build_silence_classifier_run_report(empty)
    assert report.status == "skipped_no_silence_segments"
    assert report.classification_count == 0

    # bad detection result types
    for bad in [42, "not_a_result", {"segments": "NOT_A_LIST"}]:
        report = build_silence_classifier_run_report(bad)
        assert report is not None
        assert report.status in ("failed", "skipped_no_silence_segments")

    # bad energy timeline
    detection = {
        "status": "ok",
        "segments": [{"start_seconds": 5.0, "end_seconds": 6.2, "duration_seconds": 1.2}],
    }
    bad_timeline: list[Any] = [{}, {"time_seconds": "bad", "energy_score": "bad"}]
    report = build_silence_classifier_run_report(detection, energy_timeline=bad_timeline)
    assert report is not None
    assert report.classification_count == 1


# ─── Test 6: Job roundtrip + pipeline source contract ────────────────────────

def test_2b07_job_and_pipeline_contract() -> None:
    from models.job import Job
    from shared.enums import (
        AutopublishClass,
        ChannelType,
        JobStatus,
        JobType,
        Mode,
        TargetFormat,
        ValidatorStatus,
    )

    job = Job(
        job_id="audit_job_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
    )

    # set classification fields
    job.silence_classification_report = {"status": "ok", "classification_count": 2}
    job.silence_classification_result = {"status": "ok"}
    job.silence_classification_status = "ok"
    job.silence_classifications = [
        {"classification": "filler_pause"},
        {"classification": "dead_air"},
    ]
    job.silence_classification_count = 2
    job.silence_remove_candidate_count = 2
    job.silence_keep_candidate_count = 0
    job.silence_counts_by_classification = {"filler_pause": 1, "dead_air": 1}

    data = job.to_dict()
    restored = Job.from_dict(data)

    assert restored.silence_classification_status == "ok"
    assert restored.silence_classification_count == 2
    assert restored.silence_remove_candidate_count == 2
    assert restored.silence_keep_candidate_count == 0
    assert restored.silence_counts_by_classification == {"filler_pause": 1, "dead_air": 1}
    assert len(restored.silence_classifications) == 2
    assert restored.silence_classification_report.get("status") == "ok"

    # pipeline source contract
    src = (REPO_ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")

    assert "from core.silence_classifier_runner import run_silence_classifier_for_job" in src
    assert "SILENCE_CLASSIFICATION_STARTED" in src
    assert "SILENCE_CLASSIFICATION_DONE" in src
    assert "SILENCE_CLASSIFICATION_SKIPPED" in src
    assert "SILENCE_CLASSIFICATION_FAILED" in src
    assert "silence_classification_done" in src

    detection_idx = src.find("SILENCE_DETECTION_STARTED")
    classification_idx = src.find("SILENCE_CLASSIFICATION_STARTED")
    analyzing_idx = src.find("STATE_ANALYZING")

    assert detection_idx < classification_idx < analyzing_idx, (
        "Classification must run after detection and before STATE_ANALYZING"
    )


# ─── Test 7: Integrated end-to-end flow ──────────────────────────────────────

def test_2b07_integrated_flow_detection_to_context_to_classification() -> None:
    seg1 = _seg(0.0, 0.20)
    seg2 = _seg(5.0, 1.20)
    seg3 = _seg(10.0, 2.50)

    detection = _detection([seg1, seg2, seg3])

    # energy timeline: high energy just before the 1.20s segment
    energy_timeline = [{"time_seconds": 4.5, "energy_score": 0.90}]

    report = build_silence_classifier_run_report(detection, energy_timeline=energy_timeline)

    assert report.status == "ok"
    assert report.classification_count == 3
    assert report.remove_candidate_count == 2
    assert report.keep_candidate_count == 1
    assert report.high_energy_context_count >= 1
    assert report.counts_by_classification.get("filler_pause", 0) == 1
    assert report.counts_by_classification.get("dramatic_pause", 0) == 1
    assert report.counts_by_classification.get("dead_air", 0) == 1


# ─── Test 8: BOM and newline hygiene ─────────────────────────────────────────

def test_2b07_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        REPO_ROOT / "models" / "silence_classification.py",
        REPO_ROOT / "core" / "adaptive_silence_classifier.py",
        REPO_ROOT / "models" / "silence_classifier_run.py",
        REPO_ROOT / "core" / "silence_classifier_runner.py",
        REPO_ROOT / "models" / "silence_context.py",
        REPO_ROOT / "core" / "silence_context_builder.py",
        REPO_ROOT / "tests" / "test_adaptive_silence_classifier_foundation_smoke.py",
        REPO_ROOT / "tests" / "test_silence_classifier_runner_smoke.py",
        REPO_ROOT / "tests" / "test_silence_classifier_pipeline_integration_smoke.py",
        REPO_ROOT / "tests" / "test_silence_context_builder_smoke.py",
        REPO_ROOT / "tests" / "test_silence_classifier_context_wiring_smoke.py",
        REPO_ROOT / "tests" / "test_adaptive_silence_classifier_final_audit_smoke.py",
        REPO_ROOT / "core" / "gaming_pipeline.py",
        REPO_ROOT / "models" / "job.py",
    ]
    for path in files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
