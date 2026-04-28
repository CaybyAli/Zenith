from models.job import Job
from models.edit_decision import EditDecision
from models.subtitle_asset import SubtitleAsset


class SubtitleProcessor:
    def generate(self, job: Job, edit_decision: EditDecision) -> SubtitleAsset:
        # MVP: Fake subtitles
        text = f"Auto-generated subtitles for job {job.job_id}"

        return SubtitleAsset(
            job_id=job.job_id,
            text=text,
            language="de",
            confidence=0.5,
        )