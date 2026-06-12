from pathlib import Path

from models.job import Job


def test_job_model_roundtrips_gate1b_success_lock_metrics() -> None:
    job = Job.from_dict(
        {
            "job_id": "job_gate1b_metric_roundtrip",
            "status": "approval_pending",
            "validator_status": "passed",
            "removed_speech_seconds": 0.0,
            "removed_speech_source": "dead_air_trim",
            "boundary_hits_count": 17,
            "boundary_hits_source": "phase_2b_final_review.keep_with_boundary_warning",
            "overlap_count": 0,
            "timeline_safety_overlap_count": 0,
        }
    )

    data = job.to_dict()

    assert data["removed_speech_seconds"] == 0.0
    assert data["removed_speech_source"] == "dead_air_trim"
    assert data["boundary_hits_count"] == 17
    assert data["boundary_hits_source"] == "phase_2b_final_review.keep_with_boundary_warning"
    assert data["overlap_count"] == 0
    assert data["timeline_safety_overlap_count"] == 0


def test_pipeline_runner_persists_gate1b_lock_metrics_from_pipeline_result() -> None:
    source = Path("pipeline_runner.py").read_text(encoding="utf-8")

    start = source.index('phase_2b_result = result.get("phase_2b_stabilization_result")')
    end = source.index('title_package = result.get("title_package")', start)
    block = source[start:end]

    assert 'gate1b_lock_metrics = result.get("gate1b_lock_metrics")' in block
    assert "job.removed_speech_seconds" in block
    assert "job.removed_speech_source" in block
    assert "job.boundary_hits_count" in block
    assert "job.boundary_hits_source" in block
    assert "job.overlap_count" in block
    assert "job.timeline_safety_overlap_count" in block


def test_gaming_pipeline_returns_gate1b_lock_metrics() -> None:
    source = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert '"gate1b_lock_metrics"' in source
    assert '"removed_speech_seconds"' in source
    assert '"removed_speech_source"' in source
    assert '"boundary_hits_count"' in source
    assert '"boundary_hits_source"' in source
    assert '"overlap_count"' in source
    assert '"timeline_safety_overlap_count"' in source
