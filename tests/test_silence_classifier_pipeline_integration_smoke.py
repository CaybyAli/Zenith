from __future__ import annotations

from pathlib import Path

from models.job import Job
from models.silence_classifier_run import SilenceClassifierRunReport
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


SILENCE_CLASSIFICATION_JOB_FIELDS = [
    "silence_classification_report",
    "silence_classification_result",
    "silence_classification_status",
    "silence_classifications",
    "silence_classification_count",
    "silence_remove_candidate_count",
    "silence_keep_candidate_count",
    "silence_counts_by_classification",
]


def _make_job(job_id: str = "job_silence_classification_pipeline_001") -> Job:
    return Job(
        job_id=job_id,
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


# ---------------------------------------------------------------------------
# Job-Model: round-trip + defaults
# ---------------------------------------------------------------------------

def test_job_roundtrip_preserves_silence_classification_fields() -> None:
    job = _make_job()
    job.silence_classification_report = {"status": "ok", "classification_count": 2}
    job.silence_classification_result = {"status": "ok", "classification_count": 2}
    job.silence_classification_status = "ok"
    job.silence_classifications = [
        {"classification": "filler_pause", "remove_candidate": True},
        {"classification": "sentence_gap", "remove_candidate": True},
    ]
    job.silence_classification_count = 2
    job.silence_remove_candidate_count = 2
    job.silence_keep_candidate_count = 0
    job.silence_counts_by_classification = {"filler_pause": 1, "sentence_gap": 1}

    data = job.to_dict()
    restored = Job.from_dict(data)

    for field_name in SILENCE_CLASSIFICATION_JOB_FIELDS:
        assert hasattr(restored, field_name), f"Job missing field: {field_name}"

    assert restored.silence_classification_status == "ok"
    assert restored.silence_classification_count == 2
    assert restored.silence_remove_candidate_count == 2
    assert restored.silence_keep_candidate_count == 0
    assert restored.silence_counts_by_classification == {"filler_pause": 1, "sentence_gap": 1}
    assert len(restored.silence_classifications) == 2
    assert restored.silence_classification_report.get("status") == "ok"
    assert restored.silence_classification_result.get("classification_count") == 2


def test_job_defaults_silence_classification_fields_are_neutral() -> None:
    job = _make_job()

    assert job.silence_classification_report == {}
    assert job.silence_classification_result == {}
    assert job.silence_classification_status is None
    assert job.silence_classifications == []
    assert job.silence_classification_count == 0
    assert job.silence_remove_candidate_count == 0
    assert job.silence_keep_candidate_count == 0
    assert job.silence_counts_by_classification == {}


def test_job_from_dict_does_not_crash_when_classification_fields_missing() -> None:
    job = _make_job()
    data = job.to_dict()
    for field_name in SILENCE_CLASSIFICATION_JOB_FIELDS:
        data.pop(field_name, None)

    restored = Job.from_dict(data)

    for field_name in SILENCE_CLASSIFICATION_JOB_FIELDS:
        assert hasattr(restored, field_name)
    assert restored.silence_classification_status is None
    assert restored.silence_classification_count == 0


def test_apply_pipeline_like_classification_report_sets_expected_job_fields() -> None:
    report = SilenceClassifierRunReport(
        status="ok",
        detection_status="ok",
        classification_status="ok",
        classification_result={"status": "ok", "classification_count": 3},
        classifications=[
            {"classification": "filler_pause", "remove_candidate": True},
            {"classification": "sentence_gap", "remove_candidate": True},
            {"classification": "dead_air", "remove_candidate": True},
        ],
        classification_count=3,
        remove_candidate_count=3,
        keep_candidate_count=0,
        counts_by_classification={"filler_pause": 1, "sentence_gap": 1, "dead_air": 1},
        recommendation="use_classification",
    )

    job = _make_job()
    job.silence_classification_report = report.to_dict()
    job.silence_classification_result = dict(report.classification_result or {})
    job.silence_classification_status = report.status
    job.silence_classifications = list(report.classifications or [])
    job.silence_classification_count = int(report.classification_count)
    job.silence_remove_candidate_count = int(report.remove_candidate_count)
    job.silence_keep_candidate_count = int(report.keep_candidate_count)
    job.silence_counts_by_classification = dict(report.counts_by_classification or {})

    restored = Job.from_dict(job.to_dict())

    assert restored.silence_classification_status == "ok"
    assert restored.silence_classification_count == 3
    assert restored.silence_remove_candidate_count == 3
    assert restored.silence_keep_candidate_count == 0
    assert restored.silence_counts_by_classification == {
        "filler_pause": 1,
        "sentence_gap": 1,
        "dead_air": 1,
    }
    assert restored.silence_classification_report.get("status") == "ok"
    assert restored.silence_classification_result.get("classification_count") == 3


# ---------------------------------------------------------------------------
# Pipeline source code: events + runner wiring
# ---------------------------------------------------------------------------

def test_gaming_pipeline_contains_silence_classification_events() -> None:
    src = (REPO_ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")

    assert "SILENCE_CLASSIFICATION_STARTED" in src
    assert "SILENCE_CLASSIFICATION_DONE" in src
    assert "SILENCE_CLASSIFICATION_SKIPPED" in src
    assert "SILENCE_CLASSIFICATION_FAILED" in src


def test_silence_classifier_pipeline_integration_uses_runner_import() -> None:
    src = (REPO_ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")

    assert "from core.silence_classifier_runner import run_silence_classifier_for_job" in src
    assert "run_silence_classifier_for_job(" in src


def test_silence_classification_runs_after_detection_before_state_analyzing() -> None:
    src = (REPO_ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")

    detection_started_idx = src.find("SILENCE_DETECTION_STARTED")
    classification_started_idx = src.find("SILENCE_CLASSIFICATION_STARTED")
    analyzing_idx = src.find("STATE_ANALYZING")

    assert detection_started_idx != -1, "SILENCE_DETECTION_STARTED missing"
    assert classification_started_idx != -1, "SILENCE_CLASSIFICATION_STARTED missing"
    assert analyzing_idx != -1, "STATE_ANALYZING missing"
    assert detection_started_idx < classification_started_idx < analyzing_idx, (
        "Silence classification must run after silence detection and before STATE_ANALYZING"
    )


def test_silence_classification_checkpoint_step_name_present() -> None:
    src = (REPO_ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")
    assert "silence_classification_done" in src


# ---------------------------------------------------------------------------
# Hygiene
# ---------------------------------------------------------------------------

def test_pipeline_integration_files_have_no_bom_and_end_with_newline() -> None:
    no_bom_files = [
        REPO_ROOT / "models" / "job.py",
        REPO_ROOT / "core" / "gaming_pipeline.py",
        REPO_ROOT / "tests" / "test_silence_classifier_pipeline_integration_smoke.py",
    ]
    for fpath in no_bom_files:
        raw = fpath.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {fpath}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {fpath}"
