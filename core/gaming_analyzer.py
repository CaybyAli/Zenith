from pathlib import Path

from moviepy import VideoFileClip

from models.analysis_result import AnalysisResult
from models.job import Job
from shared.errors import ValidationError


class GamingAnalyzer:
    def analyze(self, job: Job) -> AnalysisResult:
        if not job.raw_video_path:
            raise ValidationError("Gaming job has no raw_video_path")

        video_path = Path(job.raw_video_path)

        if not video_path.exists() or not video_path.is_file():
            raise ValidationError(f"Video file not found: {job.raw_video_path}")

        file_size_bytes = video_path.stat().st_size

        try:
            with VideoFileClip(str(video_path)) as clip:
                duration_seconds = float(clip.duration or 0.0)
        except Exception as exc:
            raise ValidationError(f"Could not read video duration: {exc}") from exc

        usable_for_shorts = duration_seconds >= 15
        usable_for_longform = duration_seconds >= 120

        notes = [
            f"File found: {video_path.name}",
            f"Real duration read successfully: {duration_seconds:.2f} seconds",
        ]

        return AnalysisResult(
            job_id=job.job_id,
            duration_seconds=duration_seconds,
            file_size_bytes=file_size_bytes,
            usable_for_shorts=usable_for_shorts,
            usable_for_longform=usable_for_longform,
            analysis_confidence=0.8,
            notes=notes,
        )
        