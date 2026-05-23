from __future__ import annotations

import logging
from pathlib import Path

from core.shorts_highlight_extractor import LLM_SHADOW, ShortsHighlightExtractor
from core.shorts_reframe_planner import ShortsReframePlanner
from core.shorts_render_driver import ShortsRenderDriver
from models.edit_timeline import EditTimeline
from models.job import Job
from models.transcript_result import TranscriptResult
from shared.enums import JobStatus

logger = logging.getLogger(__name__)

DEFAULT_POWER_PROFILE = "balanced"


class ShortsGenerationStage:
    def __init__(
        self,
        highlight_extractor: ShortsHighlightExtractor | None = None,
        reframe_planner: ShortsReframePlanner | None = None,
        render_driver: ShortsRenderDriver | None = None,
    ) -> None:
        self.highlight_extractor = highlight_extractor or ShortsHighlightExtractor()
        self.reframe_planner = reframe_planner or ShortsReframePlanner()
        self.render_driver = render_driver or ShortsRenderDriver()

    def run(
        self,
        job: Job,
        timeline: EditTimeline,
        source_video_path: str,
        output_base_dir: str,
        power_profile: str = DEFAULT_POWER_PROFILE,
        llm_mode: str = LLM_SHADOW,
        add_captions: bool = True,
        transcript: TranscriptResult | None = None,
    ) -> Job:
        self._set_job_status(job, JobStatus.SHORTS_GENERATING, "shorts_generation_started")

        highlights = self.highlight_extractor.extract_highlights(
            timeline,
            power_profile,
            llm_mode,
        )

        output_dir = Path(output_base_dir) / str(job.job_id) / "shorts"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            setattr(self.reframe_planner, "source_video_path", source_video_path)
        except Exception:
            pass

        for clip_index, clip in enumerate(highlights):
            clip.clip_index = clip_index

            try:
                clip.reframe_plan = self.reframe_planner.plan_reframe(
                    clip,
                    timeline,
                    llm_mode,
                )
                self.render_driver.render_short(
                    clip=clip,
                    source_video_path=source_video_path,
                    output_dir=str(output_dir),
                    job_id=str(job.job_id),
                    add_captions=add_captions,
                    transcript=transcript,
                )
            except Exception as exc:
                clip.status = "failed"
                logger.exception(
                    "Short render failed: job_id=%s clip_index=%s error=%s",
                    getattr(job, "job_id", ""),
                    clip.clip_index,
                    exc,
                )

        job.shorts_clips = list(highlights)

        rendered_count = sum(1 for clip in highlights if clip.status == "rendered")
        logger.info(
            "Shorts generation complete: %s/%s rendered",
            rendered_count,
            len(highlights),
        )

        for clip in highlights:
            layout_type = ""
            if clip.reframe_plan is not None:
                layout_type = str(getattr(clip.reframe_plan, "layout_type", "") or "")

            logger.info(
                "Short %s: %.1fs-%.1fs score=%.3f layout=%s status=%s llm='%s'",
                clip.clip_index,
                float(clip.source_start_time),
                float(clip.source_end_time),
                float(clip.hook_score),
                layout_type,
                clip.status,
                str(clip.llm_rationale or "")[:80],
            )

        self._set_job_status(job, JobStatus.SHORTS_RENDERED, "shorts_generation_finished")
        return job

    def _set_job_status(self, job: Job, status: JobStatus, reason: str) -> None:
        job.status = status

        history = list(getattr(job, "shorts_generation_status_history", []) or [])
        history.append(status.value)
        try:
            setattr(job, "shorts_generation_status_history", history)
        except Exception:
            pass

        touch = getattr(job, "touch", None)
        if callable(touch):
            try:
                touch()
            except Exception:
                pass

        logger.info(
            "Shorts generation status: job_id=%s status=%s reason=%s",
            getattr(job, "job_id", ""),
            status.value,
            reason,
        )
