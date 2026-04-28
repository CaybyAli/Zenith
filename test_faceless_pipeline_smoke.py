"""
test_faceless_pipeline_smoke.py

Smoke-tests for the Faceless pipeline:
  1. FacelessPipeline.run() — full pipeline, no GPT-4o (fallback path)
  2. FacelessPipeline.run() — GPT-4o enrichment path (mocked)
  3. pipeline_runner.run_pending_jobs() — dispatcher routes faceless jobs
  4. pipeline_runner skips gaming jobs without raw_video_path
  5. pipeline_runner.run_faceless_pipeline_for_job() — public helper
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest.mock as mock
from pathlib import Path
from types import SimpleNamespace

from core.faceless_pipeline import FacelessPipeline, _GPT4oEnricher
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


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _make_faceless_job(job_id: str = "job_faceless_smoke_001", topic: str = "sprechende KI Trend") -> Job:
    return Job(
        job_id=job_id,
        job_type=JobType.FACELESS,
        channel_type=ChannelType.FACELESS_TREND,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.CREATED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        topic=topic,
        current_module="test",
        review_status="pending",
        scheduled_at=None,
        is_scheduled=False,
    )


def _make_sample_video(path: str, duration: int = 5) -> None:
    """Create a tiny synthetic MP4 so FacelessAssembler has something to copy."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    cmd = [
        r"D:\Tools\ffmpeg\bin\ffmpeg.exe", "-y",
        "-f", "lavfi", "-i", f"testsrc=size=320x180:rate=10:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=44100:duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


# ------------------------------------------------------------------ #
#  Test 1 — full pipeline without GPT-4o (fallback metadata)          #
# ------------------------------------------------------------------ #

def test_pipeline_runs_without_gpt() -> None:
    """Pipeline must complete and produce video + metadata.json + thumbnail."""
    # FacelessAssembler looks for sample.mp4 in the CWD
    sample = Path("sample.mp4")
    sample_existed = sample.exists()
    if not sample_existed:
        _make_sample_video(str(sample))

    try:
        job = _make_faceless_job()

        # Ensure OPENAI_API_KEY is absent so we exercise the fallback path
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            result = FacelessPipeline().run(job)

        # --- structural assertions ---
        assert result["job_id"] == job.job_id
        assert result["status"] == "waiting_for_review"
        assert result["gpt_metadata_used"] is False

        # video
        assert os.path.exists(result["video_path"]), "video_path missing"

        # thumbnail
        assert os.path.exists(result["thumbnail_path"]), "thumbnail_path missing"
        assert result["thumbnail_path"].endswith(".jpg")

        # metadata.json
        assert os.path.exists(result["metadata_path"]), "metadata_path missing"
        with open(result["metadata_path"], encoding="utf-8") as f:
            meta = json.load(f)

        assert meta["job_id"] == job.job_id
        assert meta["status"] == "waiting_for_review"
        assert meta["gpt_metadata_used"] is False
        assert meta["topic"] == job.topic
        assert meta["title"]          # non-empty
        assert meta["description"]    # non-empty
        assert isinstance(meta["hashtags"], list) and len(meta["hashtags"]) >= 1

        # brief + asset_pack embedded
        assert "brief" in meta
        assert meta["brief"]["hook_direction"]
        assert "asset_pack" in meta

        print(f"\n[PASS] test_pipeline_runs_without_gpt")
        print(f"  title={result['title']!r}")
        print(f"  validator_status={result['validator_status']}")
    finally:
        if not sample_existed:
            sample.unlink(missing_ok=True)


# ------------------------------------------------------------------ #
#  Test 2 — GPT-4o enrichment path (mocked OpenAI response)           #
# ------------------------------------------------------------------ #

def test_pipeline_uses_gpt_metadata_when_available() -> None:
    """When GPT-4o returns valid data, pipeline must use it for title/description/tags."""
    sample = Path("sample.mp4")
    sample_existed = sample.exists()
    if not sample_existed:
        _make_sample_video(str(sample))

    try:
        job = _make_faceless_job(job_id="job_faceless_gpt_smoke_001")

        gpt_response_text = (
            "TITEL: Warum KI-Avatare gerade das Internet übernehmen\n"
            "BESCHREIBUNG: Sprechende KI-Charaktere sind überall – wir erklären, "
            "warum dieser Trend gerade explodiert und was dahinter steckt.\n"
            "TAGS: ki, künstlicheintelligenz, trend, viral, youtube, avatar, tech, zukunft\n"
        )

        fake_choice = SimpleNamespace(
            message=SimpleNamespace(content=gpt_response_text)
        )
        fake_response = SimpleNamespace(choices=[fake_choice])

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-fake"}):
            with mock.patch("openai.OpenAI") as mock_openai_cls:
                mock_client = mock.MagicMock()
                mock_client.chat.completions.create.return_value = fake_response
                mock_openai_cls.return_value = mock_client

                result = FacelessPipeline().run(job)

        assert result["gpt_metadata_used"] is True
        assert "KI-Avatare" in result["title"] or "KI" in result["title"]
        assert len(result["hashtags"]) >= 5

        with open(result["metadata_path"], encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["gpt_metadata_used"] is True

        print(f"\n[PASS] test_pipeline_uses_gpt_metadata_when_available")
        print(f"  title={result['title']!r}")
        print(f"  tags={result['hashtags']}")
    finally:
        if not sample_existed:
            sample.unlink(missing_ok=True)


# ------------------------------------------------------------------ #
#  Test 3 — GPT4oEnricher fallback when key is absent                  #
# ------------------------------------------------------------------ #

def test_gpt4o_enricher_returns_none_without_key() -> None:
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENAI_API_KEY", None)
        result = _GPT4oEnricher().enrich(
            topic="Test-Trend",
            hook="Das Internet redet gerade darüber",
            script_excerpt="Kurzes Script",
        )
    assert result is None
    print(f"\n[PASS] test_gpt4o_enricher_returns_none_without_key")


# ------------------------------------------------------------------ #
#  Test 4 — pipeline_runner dispatches faceless jobs                   #
# ------------------------------------------------------------------ #

def test_pipeline_runner_routes_faceless_job() -> None:
    """run_pending_jobs() must pick up a CREATED faceless job and process it."""
    sample = Path("sample.mp4")
    sample_existed = sample.exists()
    if not sample_existed:
        _make_sample_video(str(sample))

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "jobs.json")

        from core.job_store import JobStore
        job_store = JobStore(db_path=db_path)

        job = _make_faceless_job(job_id="job_runner_faceless_001")
        job_store.create_job(job)

        from pipeline_runner import run_pending_jobs

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            results = run_pending_jobs(db_path=db_path)

        assert len(results) == 1
        r = results[0]
        assert r["job_id"] == job.job_id
        assert r["status"] == "ok", f"Expected ok, got: {r}"
        assert r["pipeline"] == "faceless"
        assert r["result"]["status"] == "waiting_for_review"

        # job store must be updated
        updated = job_store.get_job(job.job_id)
        assert updated.status == JobStatus.ROUTED
        assert updated.review_status == "waiting_for_review"

        print(f"\n[PASS] test_pipeline_runner_routes_faceless_job")
        print(f"  video_path={r['result']['video_path']!r}")
    if not sample_existed:
        sample.unlink(missing_ok=True)


# ------------------------------------------------------------------ #
#  Test 5 — pipeline_runner skips gaming job without video path        #
# ------------------------------------------------------------------ #

def test_pipeline_runner_skips_gaming_without_video() -> None:
    """Gaming jobs with no raw_video_path must be skipped gracefully."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "jobs.json")

        from core.job_store import JobStore
        job_store = JobStore(db_path=db_path)

        gaming_job = Job(
            job_id="job_runner_gaming_skip_001",
            job_type=JobType.GAMING,
            channel_type=ChannelType.GAMING_MAIN,
            target_format=TargetFormat.LONGFORM,
            target_platforms=["youtube"],
            status=JobStatus.CREATED,
            mode=Mode.NORMAL,
            autopublish_class=AutopublishClass.MANUAL_ONLY,
            confidence_score=0.0,
            validator_status=ValidatorStatus.NOT_VALIDATED,
            raw_video_path=None,   # ← deliberately absent
            current_module="test",
            review_status="pending",
            scheduled_at=None,
            is_scheduled=False,
        )
        job_store.create_job(gaming_job)

        from pipeline_runner import run_pending_jobs
        results = run_pending_jobs(db_path=db_path)

        assert len(results) == 1
        r = results[0]
        assert r["status"] == "skip"
        assert r["reason"] == "no_raw_video_path"

        print(f"\n[PASS] test_pipeline_runner_skips_gaming_without_video")


# ------------------------------------------------------------------ #
#  Test 6 — public helper run_faceless_pipeline_for_job                #
# ------------------------------------------------------------------ #

def test_run_faceless_pipeline_for_job_helper() -> None:
    """The public helper in pipeline_runner must work standalone."""
    sample = Path("sample.mp4")
    sample_existed = sample.exists()
    if not sample_existed:
        _make_sample_video(str(sample))

    try:
        job = _make_faceless_job(job_id="job_helper_faceless_001")

        from pipeline_runner import run_faceless_pipeline_for_job

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            result = run_faceless_pipeline_for_job(job)

        assert result["status"] == "waiting_for_review"
        assert os.path.exists(result["video_path"])
        assert os.path.exists(result["metadata_path"])

        print(f"\n[PASS] test_run_faceless_pipeline_for_job_helper")
    finally:
        if not sample_existed:
            sample.unlink(missing_ok=True)


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

def main() -> None:
    test_gpt4o_enricher_returns_none_without_key()
    test_pipeline_runs_without_gpt()
    test_pipeline_uses_gpt_metadata_when_available()
    test_pipeline_runner_routes_faceless_job()
    test_pipeline_runner_skips_gaming_without_video()
    test_run_faceless_pipeline_for_job_helper()
    print("\n=== ALL FACELESS PIPELINE SMOKE TESTS PASSED ===")


if __name__ == "__main__":
    main()
