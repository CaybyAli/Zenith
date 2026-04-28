from models.job import Job
from models.title_package import TitlePackage


class TitleGenerator:
    def generate(self, job: Job) -> TitlePackage:
        if job.job_type.value == "gaming":
            title = "Unfassbarer Gaming Moment 😱🔥"
            backups = [
                "Das ist komplett eskaliert 😳",
                "Ich konnte es selbst nicht glauben 😱"
            ]
        else:
            title = f"{job.topic} – das geht viral 😳"
            backups = [
                f"Warum {job.topic} gerade im Trend ist",
                f"Das Internet dreht durch wegen {job.topic}"
            ]

        return TitlePackage(
            job_id=job.job_id,
            primary_title=title,
            backup_titles=backups,
            title_score=0.7,
        )