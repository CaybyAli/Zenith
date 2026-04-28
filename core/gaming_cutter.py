from models.analysis_result import AnalysisResult
from models.edit_decision import EditDecision
from models.job import Job
from shared.errors import ValidationError


class GamingCutter:
    def build_cut(self, job: Job, analysis_result: AnalysisResult) -> EditDecision:
        if not job.raw_video_path:
            raise ValidationError("Gaming cutter needs a gaming job with raw_video_path")

        if analysis_result.duration_seconds <= 0:
            raise ValidationError("Invalid analysis result: duration must be greater than 0")

        if analysis_result.usable_for_shorts:
            target_runtime = min(analysis_result.duration_seconds, 60.0)
            selected_segments = [f"0.0s - {target_runtime:.1f}s"]
            removed_segments = []
            hook_candidate_range = "0.0s - 3.0s"
            cut_style = "short_highlight"
            cut_confidence = 0.8
        else:
            selected_segments = ["0.0s - end"]
            removed_segments = []
            target_runtime = analysis_result.duration_seconds
            hook_candidate_range = "0.0s - 2.0s"
            cut_style = "basic_full_clip"
            cut_confidence = 0.5

        return EditDecision(
            job_id=job.job_id,
            selected_segments=selected_segments,
            removed_segments=removed_segments,
            target_runtime=target_runtime,
            hook_candidate_range=hook_candidate_range,
            cut_style=cut_style,
            cut_confidence=cut_confidence,
        )