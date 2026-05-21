from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

import pytest

from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path
from core.power_profile import PowerProfile
from core.shorts_generation_stage import ShortsGenerationStage
from core.shorts_render_driver import ShortsRenderDriver
from models.edit_timeline import EditTimeline
from models.shorts_clip import ShortsClip
from models.shorts_reframe_plan import ShortsReframePlan
from models.timeline_segment import TimelineSegment
from shared.enums import JobStatus

JOB_ID = "job_shorts_generation_stage_test"


class DummyJob:
    def __init__(self) -> None:
        self.job_id = JOB_ID
        self.status = JobStatus.RENDERED
        self.shorts_clips = []
        self.power_profile = PowerProfile.BALANCED

    def touch(self) -> None:
        return None


def _clip(index: int) -> ShortsClip:
    start = float(index * 20)
    return ShortsClip(
        source_job_id=JOB_ID,
        source_start_time=start,
        source_end_time=start + 8.0,
        planned_duration=8.0,
        reframe_plan=None,
        hook_score=0.9 - index * 0.05,
        llm_rationale=f"clip {index} rationale",
        status="planned",
        clip_index=index,
        output_path="",
    )


def _timeline() -> EditTimeline:
    segments = [
        TimelineSegment(
            segment_id=f"seg_{index}",
            job_id=JOB_ID,
            candidate_id=None,
            start_time=float(index * 20),
            end_time=float(index * 20 + 8),
            segment_role="highlight",
            selection_score=0.9 - index * 0.05,
        )
        for index in range(5)
    ]
    return EditTimeline(
        timeline_id="timeline_shorts_generation_stage_test",
        job_id=JOB_ID,
        target_duration=40.0,
        selected_segments=segments,
        timeline_score=1.0,
    )


class MockHighlightExtractor:
    def extract_highlights(self, timeline, power_profile, llm_mode):
        counts = {
            PowerProfile.ECO: 1,
            PowerProfile.BALANCED: 3,
            PowerProfile.PERFORMANCE: 5,
            PowerProfile.FULL_POWER: 5,
            "eco": 1,
            "balanced": 3,
            "performance": 5,
            "full_power": 5,
        }
        count = counts.get(power_profile, 3)
        return [_clip(index) for index in range(count)]


class MockReframePlanner:
    def plan_reframe(self, clip, timeline, llm_mode):
        return ShortsReframePlan(
            layout_type="gameplay_centered",
            ffmpeg_crop_filter="crop=1080:1920:420:0",
            layout_rationale="mock layout",
        )


class MockRenderDriver:
    def __init__(self, fail_indices=None) -> None:
        self.fail_indices = set(fail_indices or [])

    def render_short(
        self,
        clip,
        source_video_path,
        output_dir,
        job_id,
        add_captions=True,
    ):
        if clip.clip_index in self.fail_indices:
            raise RuntimeError(f"mock render failed for {clip.clip_index}")

        output_path = str(Path(output_dir) / f"{job_id}_short_{clip.clip_index}.mp4")
        clip.output_path = output_path
        clip.status = "rendered"
        return output_path


def _stage(render_driver=None):
    return ShortsGenerationStage(
        highlight_extractor=MockHighlightExtractor(),
        reframe_planner=MockReframePlanner(),
        render_driver=render_driver or MockRenderDriver(),
    )


def test_run_transitions_from_shorts_generating_to_shorts_rendered(tmp_path: Path) -> None:
    job = DummyJob()

    result = _stage().run(
        job=job,
        timeline=_timeline(),
        source_video_path="source.mp4",
        output_base_dir=str(tmp_path),
        power_profile=PowerProfile.BALANCED,
    )

    assert result.status == JobStatus.SHORTS_RENDERED
    assert result.shorts_generation_status_history == [
        JobStatus.SHORTS_GENERATING.value,
        JobStatus.SHORTS_RENDERED.value,
    ]


def test_balanced_creates_three_shorts(tmp_path: Path) -> None:
    job = DummyJob()

    _stage().run(
        job=job,
        timeline=_timeline(),
        source_video_path="source.mp4",
        output_base_dir=str(tmp_path),
        power_profile=PowerProfile.BALANCED,
    )

    assert len(job.shorts_clips) == 3


def test_one_failed_clip_does_not_stop_remaining_clips(tmp_path: Path) -> None:
    job = DummyJob()

    _stage(MockRenderDriver(fail_indices={1})).run(
        job=job,
        timeline=_timeline(),
        source_video_path="source.mp4",
        output_base_dir=str(tmp_path),
        power_profile=PowerProfile.BALANCED,
    )

    assert [clip.status for clip in job.shorts_clips] == ["rendered", "failed", "rendered"]


def test_all_failed_clips_still_finish_job_status(tmp_path: Path, caplog) -> None:
    caplog.set_level(logging.INFO, logger="core.shorts_generation_stage")
    job = DummyJob()

    _stage(MockRenderDriver(fail_indices={0, 1, 2})).run(
        job=job,
        timeline=_timeline(),
        source_video_path="source.mp4",
        output_base_dir=str(tmp_path),
        power_profile=PowerProfile.BALANCED,
    )

    assert job.status == JobStatus.SHORTS_RENDERED
    assert "Shorts generation complete: 0/3 rendered" in caplog.text


def test_eco_generates_one_short(tmp_path: Path) -> None:
    job = DummyJob()

    _stage().run(
        job=job,
        timeline=_timeline(),
        source_video_path="source.mp4",
        output_base_dir=str(tmp_path),
        power_profile=PowerProfile.ECO,
    )

    assert len(job.shorts_clips) == 1


def test_performance_generates_five_shorts(tmp_path: Path) -> None:
    job = DummyJob()

    _stage().run(
        job=job,
        timeline=_timeline(),
        source_video_path="source.mp4",
        output_base_dir=str(tmp_path),
        power_profile=PowerProfile.PERFORMANCE,
    )

    assert len(job.shorts_clips) == 5


def test_summary_log_contains_rendered_count(tmp_path: Path, caplog) -> None:
    caplog.set_level(logging.INFO, logger="core.shorts_generation_stage")
    job = DummyJob()

    _stage(MockRenderDriver(fail_indices={1})).run(
        job=job,
        timeline=_timeline(),
        source_video_path="source.mp4",
        output_base_dir=str(tmp_path),
        power_profile=PowerProfile.BALANCED,
    )

    assert "Shorts generation complete: 2/3 rendered" in caplog.text


def test_per_clip_log_contains_required_fields(tmp_path: Path, caplog) -> None:
    caplog.set_level(logging.INFO, logger="core.shorts_generation_stage")
    job = DummyJob()

    _stage().run(
        job=job,
        timeline=_timeline(),
        source_video_path="source.mp4",
        output_base_dir=str(tmp_path),
        power_profile=PowerProfile.BALANCED,
    )

    assert "Short 0: 0.0s-8.0s" in caplog.text
    assert "score=0.900" in caplog.text
    assert "layout=gameplay_centered" in caplog.text
    assert "status=rendered" in caplog.text


def test_each_rendered_clip_has_reframe_plan(tmp_path: Path) -> None:
    job = DummyJob()

    _stage().run(
        job=job,
        timeline=_timeline(),
        source_video_path="source.mp4",
        output_base_dir=str(tmp_path),
        power_profile=PowerProfile.BALANCED,
    )

    assert all(clip.reframe_plan is not None for clip in job.shorts_clips)


def test_output_path_is_set_after_successful_render(tmp_path: Path) -> None:
    job = DummyJob()

    _stage().run(
        job=job,
        timeline=_timeline(),
        source_video_path="source.mp4",
        output_base_dir=str(tmp_path),
        power_profile=PowerProfile.BALANCED,
    )

    assert all(clip.output_path for clip in job.shorts_clips)


class FixedThreeHighlightExtractor:
    def extract_highlights(self, timeline, power_profile, llm_mode):
        return [
            ShortsClip(
                source_job_id=JOB_ID,
                source_start_time=0.0,
                source_end_time=8.0,
                planned_duration=8.0,
                hook_score=0.9,
                clip_index=0,
            ),
            ShortsClip(
                source_job_id=JOB_ID,
                source_start_time=10.0,
                source_end_time=18.0,
                planned_duration=8.0,
                hook_score=0.85,
                clip_index=1,
            ),
            ShortsClip(
                source_job_id=JOB_ID,
                source_start_time=20.0,
                source_end_time=28.0,
                planned_duration=8.0,
                hook_score=0.8,
                clip_index=2,
            ),
        ]


def _run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        shell=False,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.shorts_render_integration
def test_real_multi_shorts_generation_renders_three_vertical_clips(tmp_path: Path) -> None:
    ffmpeg_path = get_ffmpeg_path()
    ffprobe_path = get_ffprobe_path()

    source_path = tmp_path / "source_30s.mp4"
    create_source = [
        ffmpeg_path,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=1920x1080:r=60:d=30",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=48000:d=30",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        str(source_path),
    ]
    created = _run(create_source)
    if created.returncode != 0:
        pytest.skip(f"synthetic source creation failed: {created.stderr}")

    job = DummyJob()
    stage = ShortsGenerationStage(
        highlight_extractor=FixedThreeHighlightExtractor(),
        reframe_planner=MockReframePlanner(),
        render_driver=ShortsRenderDriver(power_profile=PowerProfile.BALANCED),
    )

    stage.run(
        job=job,
        timeline=_timeline(),
        source_video_path=str(source_path),
        output_base_dir=str(tmp_path / "exports"),
        power_profile=PowerProfile.BALANCED,
        add_captions=False,
    )

    assert len(job.shorts_clips) == 3
    assert all(clip.status == "rendered" for clip in job.shorts_clips)

    probe_codec_names = ShortsRenderDriver(
        power_profile=PowerProfile.BALANCED
    ).expected_probe_codec_names()

    for clip in job.shorts_clips:
        output_path = Path(clip.output_path)
        ffprobe_cmd = [
            ffprobe_path,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(output_path),
        ]
        probed = _run(ffprobe_cmd)
        print("ffprobe command:", ffprobe_cmd)
        print("ffprobe stdout:", probed.stdout)
        print("ffprobe stderr:", probed.stderr)

        assert probed.returncode == 0
        payload = json.loads(probed.stdout)
        streams = payload.get("streams", [])
        video_stream = next(stream for stream in streams if stream.get("codec_type") == "video")
        duration = float(payload.get("format", {}).get("duration", 0.0))

        assert 7.0 <= duration <= 9.0
        assert int(video_stream.get("width")) == 1080
        assert int(video_stream.get("height")) == 1920
        assert video_stream.get("codec_name") in probe_codec_names
